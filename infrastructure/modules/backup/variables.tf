variable "environment" {
  type        = string
  description = "Deployment environment (staging, production)."
}

variable "cluster_name" {
  type        = string
  description = "Cluster name prefix for resource naming."
}

variable "aws_region" {
  type        = string
  description = "AWS region for S3 bucket."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL password for backup job credentials."
}

variable "backup_retention_days" {
  type        = number
  default     = 30
  description = "Number of days to retain backup files in S3."
}

variable "oidc_provider_arn" {
  type        = string
  description = "ARN of the EKS OIDC identity provider for IRSA."
}

variable "oidc_provider_url" {
  type        = string
  description = "URL of the EKS OIDC identity provider (without https://)."
}
