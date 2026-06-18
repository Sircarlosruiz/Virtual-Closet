variable "cluster_name" {
  type        = string
  description = "Name prefix for cluster resources."
}

variable "datacenter_location" {
  type        = string
  description = "Hetzner datacenter location (nbg1, fsn1, hel1)."
}

variable "k3s_version" {
  type        = string
  description = "Pinned k3s version string (e.g. v1.29.4+k3s1). See ADR-032."
}

variable "network_id" {
  type        = string
  description = "Hetzner private network ID from vpc module."
}

variable "firewall_id" {
  type        = string
  description = "Hetzner firewall ID from vpc module."
}

variable "ssh_key_id" {
  type        = string
  description = "Hetzner SSH key ID for node access."
}

variable "ssh_private_key_path" {
  type        = string
  sensitive   = true
  description = "Local path to SSH private key for remote-exec provisioners."
}
