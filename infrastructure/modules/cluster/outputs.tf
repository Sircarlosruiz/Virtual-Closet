output "control_plane_public_ip" {
  description = "Public IPv4 of control-plane node."
  value       = hcloud_server.control_plane.ipv4_address
}

output "worker_public_ip" {
  description = "Public IPv4 of worker node."
  value       = hcloud_server.worker.ipv4_address
}

output "kubeconfig" {
  description = "kubeconfig content with public IP substituted. Store as CI/CD secret."
  value       = replace(data.remote_file.kubeconfig.content, "127.0.0.1", hcloud_server.control_plane.ipv4_address)
  sensitive   = true
}

output "k3s_token" {
  description = "k3s node join token. Required to add additional worker nodes."
  value       = data.remote_file.k3s_token.content
  sensitive   = true
}
