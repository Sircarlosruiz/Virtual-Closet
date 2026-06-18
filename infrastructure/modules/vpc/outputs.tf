output "network_id" {
  description = "Hetzner private network ID."
  value       = hcloud_network.main.id
}

output "subnet_id" {
  description = "Hetzner private network subnet ID."
  value       = hcloud_network_subnet.nodes.id
}

output "firewall_id" {
  description = "Hetzner firewall ID applied to all cluster nodes."
  value       = hcloud_firewall.main.id
}
