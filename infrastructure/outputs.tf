output "control_plane_public_ip" {
  description = "Public IPv4 of the k3s control-plane node."
  value       = module.cluster.control_plane_public_ip
}

output "worker_public_ip" {
  description = "Public IPv4 of the k3s worker node."
  value       = module.cluster.worker_public_ip
}

output "kubeconfig" {
  description = "kubeconfig file content for kubectl access. Store in CI/CD as KUBECONFIG_STAGING secret."
  value       = module.cluster.kubeconfig
  sensitive   = true
}

output "k3s_token" {
  description = "k3s node join token. Required when adding additional worker nodes."
  value       = module.cluster.k3s_token
  sensitive   = true
}

output "backup_bucket_name" {
  description = "Hetzner Object Storage bucket name for PostgreSQL backups."
  value       = module.backup.bucket_name
}
