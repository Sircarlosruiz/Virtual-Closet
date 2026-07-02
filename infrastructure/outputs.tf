output "cluster_endpoint" {
  description = "EKS cluster API server endpoint."
  value       = module.cluster.cluster_endpoint
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = module.cluster.cluster_name
}

output "cluster_ca_certificate" {
  description = "EKS cluster CA certificate (base64-encoded)."
  value       = module.cluster.cluster_ca_certificate
  sensitive   = true
}

output "backup_bucket_name" {
  description = "S3 bucket name for PostgreSQL backups."
  value       = module.backup.bucket_name
}

output "kubeconfig_command" {
  description = "Command to generate kubeconfig for kubectl access."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.cluster.cluster_name}"
}
