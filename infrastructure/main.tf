locals {
  common_tags = {
    environment = var.environment
    managed_by  = "terraform"
    project     = "virtualcloset"
  }
}

module "vpc" {
  source = "./modules/vpc"

  cluster_name = var.cluster_name
  admin_cidrs  = var.admin_cidrs
}

module "cluster" {
  source = "./modules/cluster"

  cluster_name             = var.cluster_name
  aws_region               = var.aws_region
  eks_kubernetes_version   = var.eks_kubernetes_version
  vpc_id                   = module.vpc.vpc_id
  private_subnet_ids       = module.vpc.private_subnet_ids
  node_instance_type       = var.node_instance_type
  node_desired_size        = var.node_desired_size
  node_min_size            = var.node_min_size
  node_max_size            = var.node_max_size
  ssh_public_key_path      = var.ssh_public_key_path
  admin_cidrs              = var.admin_cidrs
  node_security_group_id   = module.vpc.node_security_group_id

  depends_on = [module.vpc]
}

module "backup" {
  source = "./modules/backup"

  environment        = var.environment
  cluster_name       = var.cluster_name
  aws_region         = var.aws_region
  postgres_password  = var.postgres_password
  backup_retention_days = var.backup_retention_days
  oidc_provider_arn  = module.cluster.oidc_provider_arn
  oidc_provider_url  = module.cluster.oidc_provider_url

  depends_on = [module.cluster]
}
