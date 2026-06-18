variable "hcloud_token" {
  type        = string
  sensitive   = true
  description = "Hetzner Cloud API token. Set via HCLOUD_TOKEN env var or Terraform Cloud variable (sensitive)."
}

variable "cluster_name" {
  type        = string
  default     = "virtualcloset-staging"
  description = "Name prefix for all Hetzner resources."
}

variable "datacenter_location" {
  type        = string
  default     = "nbg1"
  description = "Hetzner datacenter location. EU only for GDPR compliance."
  validation {
    condition     = contains(["nbg1", "fsn1", "hel1"], var.datacenter_location)
    error_message = "Must be an EU datacenter: nbg1 (Nuremberg), fsn1 (Falkenstein), or hel1 (Helsinki)."
  }
}

variable "k3s_version" {
  type        = string
  default     = "v1.29.4+k3s1"
  description = "Pinned k3s version. Change intentionally and test in staging first. See ADR-032."
}

variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed SSH (22) and kubectl (6443) access. Use static IPs only."
  # Example: ["203.0.113.10/32", "198.51.100.20/32"]
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key content for node access (e.g. contents of ~/.ssh/id_rsa.pub)."
}

variable "ssh_private_key_path" {
  type        = string
  sensitive   = true
  default     = "~/.ssh/id_rsa"
  description = "Path to SSH private key on the machine running Terraform. Used for remote-exec provisioners."
}

variable "environment" {
  type        = string
  default     = "staging"
  description = "Deployment environment. Affects resource naming and backup bucket."
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Must be staging or production."
  }
}

variable "object_storage_access_key" {
  type        = string
  sensitive   = true
  description = "Hetzner Object Storage access key for backup bucket and Terraform state fallback."
}

variable "object_storage_secret_key" {
  type        = string
  sensitive   = true
  description = "Hetzner Object Storage secret key."
}

variable "object_storage_endpoint" {
  type        = string
  default     = "https://fsn1.your-objectstorage.com"
  description = "Hetzner Object Storage S3-compatible endpoint URL."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL superuser password. Used to create the backup k8s Secret."
}
