locals {
  common_tags = {
    environment = var.environment
    managed_by  = "terraform"
    project     = "virtualcloset"
  }
}

# SSH key uploaded to Hetzner for node access
resource "hcloud_ssh_key" "admin" {
  name       = "${var.cluster_name}-admin"
  public_key = var.ssh_public_key
}

# Write kubeconfig to a temp file so the kubernetes provider can use it
resource "local_file" "kubeconfig" {
  content         = module.cluster.kubeconfig
  filename        = "${path.module}/.kubeconfig"
  file_permission = "0600"
}

module "vpc" {
  source = "./modules/vpc"

  cluster_name = var.cluster_name
  admin_cidrs  = var.admin_cidrs
}

module "cluster" {
  source = "./modules/cluster"

  cluster_name         = var.cluster_name
  datacenter_location  = var.datacenter_location
  k3s_version          = var.k3s_version
  network_id           = module.vpc.network_id
  firewall_id          = module.vpc.firewall_id
  ssh_key_id           = hcloud_ssh_key.admin.id
  ssh_private_key_path = var.ssh_private_key_path
}

module "backup" {
  source = "./modules/backup"

  environment               = var.environment
  cluster_name              = var.cluster_name
  object_storage_access_key = var.object_storage_access_key
  object_storage_secret_key = var.object_storage_secret_key
  object_storage_endpoint   = var.object_storage_endpoint
  postgres_password         = var.postgres_password

  depends_on = [module.cluster]
}
