variable "environment" {
  type        = string
  description = "Deployment environment (staging, production)."
}

variable "cluster_name" {
  type        = string
  description = "Cluster name prefix for resource naming."
}

variable "object_storage_access_key" {
  type        = string
  sensitive   = true
  description = "Hetzner Object Storage access key for backup bucket."
}

variable "object_storage_secret_key" {
  type        = string
  sensitive   = true
  description = "Hetzner Object Storage secret key."
}

variable "object_storage_endpoint" {
  type        = string
  description = "S3-compatible endpoint URL (e.g. https://fsn1.your-objectstorage.com)."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL password for backup job credentials."
}

variable "backup_schedule" {
  type        = string
  default     = "0 2 * * *"
  description = "Cron schedule for PostgreSQL backup job. Default: 02:00 UTC daily."
}

variable "backup_retention_days" {
  type        = number
  default     = 30
  description = "Number of days to retain backup files in Object Storage."
}
