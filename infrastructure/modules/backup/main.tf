resource "aws_s3_bucket" "backups" {
  bucket = "${var.cluster_name}-backups-${var.environment}"

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

    rule {
      id     = "expire-old-backups"
      status = "Enabled"

      filter {
        prefix = ""
      }

      expiration {
        days = var.backup_retention_days
      }

      noncurrent_version_expiration {
        noncurrent_days = var.backup_retention_days
      }
    }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_policy" "backup_access" {
  name        = "${var.cluster_name}-backup-s3-access"
  description = "Allow backup CronJob to write to S3 backup bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject",
        ]
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*",
        ]
      }
    ]
  })
}

resource "aws_iam_role" "backup" {
  name = "${var.cluster_name}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_provider_url}:sub" = "system:serviceaccount:virtual-closet-staging:postgres-backup-sa"
          "${var.oidc_provider_url}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  policy_arn = aws_iam_policy.backup_access.arn
  role       = aws_iam_role.backup.name
}

resource "kubernetes_service_account" "backup" {
  metadata {
    name      = "postgres-backup-sa"
    namespace = "virtual-closet-staging"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.backup.arn
    }
  }
}

resource "kubernetes_secret" "postgres_backup" {
  metadata {
    name      = "postgres-backup-credentials"
    namespace = "virtual-closet-staging"
  }

  data = {
    password = var.postgres_password
  }
}

resource "kubernetes_manifest" "backup_cronjob" {
  manifest = {
    apiVersion = "batch/v1"
    kind       = "CronJob"
    metadata = {
      name      = "postgres-backup"
      namespace = "virtual-closet-staging"
    }
    spec = {
      schedule                 = "0 2 * * *"
      concurrencyPolicy        = "Forbid"
      successfulJobsHistoryLimit = 3
      failedJobsHistoryLimit   = 3
      jobTemplate = {
        spec = {
          template = {
            spec = {
              serviceAccountName = "postgres-backup-sa"
              restartPolicy      = "OnFailure"
              containers = [{
                name    = "backup"
                image   = "postgres:16-alpine"
                command = ["/bin/sh", "-c"]
                args = [<<-EOT
                  set -e
                  apk add --no-cache aws-cli > /dev/null 2>&1
                  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                  BACKUP_FILE="backup_$${TIMESTAMP}.sql.gz"
                  echo "Starting backup: $${BACKUP_FILE}"
                  pg_dump -h postgres -U postgres virtual_closet | gzip > /tmp/$${BACKUP_FILE}
                  aws s3 cp /tmp/$${BACKUP_FILE} "s3://$${BUCKET_NAME}/$${BACKUP_FILE}" \
                    --region "$${AWS_REGION}"
                  echo "Backup uploaded: $${BACKUP_FILE} ($(du -sh /tmp/$${BACKUP_FILE} | cut -f1))"
                  rm /tmp/$${BACKUP_FILE}
                  echo "Done"
                EOT
                ]
                env = [
                  {
                    name = "PGPASSWORD"
                    valueFrom = {
                      secretKeyRef = {
                        name = "postgres-backup-credentials"
                        key  = "password"
                      }
                    }
                  },
                  {
                    name  = "BUCKET_NAME"
                    value = aws_s3_bucket.backups.bucket
                  },
                  {
                    name  = "AWS_REGION"
                    value = var.aws_region
                  },
                ]
              }]
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_secret.postgres_backup,
    kubernetes_service_account.backup,
  ]
}
