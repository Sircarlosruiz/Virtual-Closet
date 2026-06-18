module "staging" {
  source = "../../"

  environment         = "staging"
  cluster_name        = "virtualcloset-staging"
  datacenter_location = "nbg1"
  k3s_version         = "v1.29.4+k3s1"

  # Sensitive — set as Terraform Cloud workspace variables (sensitive=true)
  hcloud_token              = var.hcloud_token
  ssh_public_key            = var.ssh_public_key
  ssh_private_key_path      = var.ssh_private_key_path
  admin_cidrs               = var.admin_cidrs
  object_storage_access_key = var.object_storage_access_key
  object_storage_secret_key = var.object_storage_secret_key
  postgres_password         = var.postgres_password
}

variable "hcloud_token"              { sensitive = true }
variable "ssh_public_key"            {}
variable "ssh_private_key_path"      { sensitive = true; default = "~/.ssh/id_rsa" }
variable "admin_cidrs"               { type = list(string) }
variable "object_storage_access_key" { sensitive = true }
variable "object_storage_secret_key" { sensitive = true }
variable "postgres_password"         { sensitive = true }

output "control_plane_public_ip" { value = module.staging.control_plane_public_ip }
output "worker_public_ip"        { value = module.staging.worker_public_ip }
output "backup_bucket_name"      { value = module.staging.backup_bucket_name }
