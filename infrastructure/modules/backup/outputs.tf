output "bucket_name" {
  description = "Object Storage bucket name for PostgreSQL backups."
  value       = local.bucket_name
}

output "cronjob_name" {
  description = "Kubernetes CronJob name for the backup job."
  value       = "postgres-backup"
}
