locals {
  bucket_name = "virtualcloset-backups-${var.environment}"
}

# k8s Secret: Object Storage credentials for backup CronJob
resource "kubernetes_secret" "object_storage" {
  metadata {
    name      = "object-storage-credentials"
    namespace = "default"
  }

  data = {
    access_key = var.object_storage_access_key
    secret_key = var.object_storage_secret_key
    endpoint   = var.object_storage_endpoint
    bucket     = local.bucket_name
  }
}

# k8s Secret: PostgreSQL credentials for pg_dump
resource "kubernetes_secret" "postgres_backup" {
  metadata {
    name      = "postgres-backup-credentials"
    namespace = "default"
  }

  data = {
    password = var.postgres_password
  }
}

# Backup CronJob — pg_dump daily at 02:00 UTC → Hetzner Object Storage
resource "kubernetes_manifest" "backup_cronjob" {
  manifest = {
    apiVersion = "batch/v1"
    kind       = "CronJob"
    metadata = {
      name      = "postgres-backup"
      namespace = "default"
    }
    spec = {
      schedule                 = var.backup_schedule
      concurrencyPolicy        = "Forbid"
      successfulJobsHistoryLimit = 3
      failedJobsHistoryLimit   = 3
      jobTemplate = {
        spec = {
          template = {
            spec = {
              restartPolicy = "OnFailure"
              nodeSelector = {
                "virtualcloset.io/role" = "worker"
              }
              containers = [{
                name  = "backup"
                image = "postgres:15-alpine"
                command = ["/bin/sh", "-c"]
                args = [<<-EOT
                  set -e
                  apk add --no-cache aws-cli > /dev/null 2>&1
                  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                  BACKUP_FILE="backup_$${TIMESTAMP}.sql.gz"
                  echo "Starting backup: $${BACKUP_FILE}"
                  pg_dump -h postgres -U postgres virtual_closet | gzip > /tmp/$${BACKUP_FILE}
                  aws s3 cp /tmp/$${BACKUP_FILE} "s3://$${BUCKET_NAME}/$${BACKUP_FILE}" \
                    --endpoint-url "$${S3_ENDPOINT}"
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
                    name = "AWS_ACCESS_KEY_ID"
                    valueFrom = {
                      secretKeyRef = {
                        name = "object-storage-credentials"
                        key  = "access_key"
                      }
                    }
                  },
                  {
                    name = "AWS_SECRET_ACCESS_KEY"
                    valueFrom = {
                      secretKeyRef = {
                        name = "object-storage-credentials"
                        key  = "secret_key"
                      }
                    }
                  },
                  {
                    name = "S3_ENDPOINT"
                    valueFrom = {
                      secretKeyRef = {
                        name = "object-storage-credentials"
                        key  = "endpoint"
                      }
                    }
                  },
                  {
                    name = "BUCKET_NAME"
                    valueFrom = {
                      secretKeyRef = {
                        name = "object-storage-credentials"
                        key  = "bucket"
                      }
                    }
                  },
                  {
                    name  = "AWS_DEFAULT_REGION"
                    value = "eu-central-1"
                  }
                ]
              }]
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_secret.object_storage,
    kubernetes_secret.postgres_backup,
  ]
}
