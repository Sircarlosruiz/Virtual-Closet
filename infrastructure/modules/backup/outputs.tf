output "bucket_name" {
  description = "S3 bucket name for PostgreSQL backups."
  value       = aws_s3_bucket.backups.bucket
}

output "bucket_arn" {
  description = "S3 bucket ARN."
  value       = aws_s3_bucket.backups.arn
}

output "cronjob_name" {
  description = "Kubernetes CronJob name for the backup job."
  value       = "postgres-backup"
}
