module "staging" {
  source = "../../"

  environment            = "staging"
  cluster_name           = "virtualcloset-staging"
  aws_region             = "us-west-2"
  eks_kubernetes_version = "1.30"
  node_instance_type     = "t3.large"
  node_desired_size      = 2
  node_min_size          = 1
  node_max_size          = 3

  admin_cidrs           = var.admin_cidrs
  ssh_public_key_path   = var.ssh_public_key_path
  postgres_password     = var.postgres_password
}

variable "admin_cidrs"         { type = list(string) }
variable "ssh_public_key_path" { default = "~/.ssh/id_rsa.pub" }
variable "postgres_password"   { sensitive = true }

output "cluster_endpoint"     { value = module.staging.cluster_endpoint }
output "cluster_name"         { value = module.staging.cluster_name }
output "backup_bucket_name"   { value = module.staging.backup_bucket_name }
output "kubeconfig_command"   { value = module.staging.kubeconfig_command }
