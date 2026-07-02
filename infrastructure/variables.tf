variable "aws_region" {
  type        = string
  default     = "us-west-2"
  description = "AWS region for all resources."
  validation {
    condition     = contains(["us-east-1", "us-west-2", "eu-central-1", "eu-west-1"], var.aws_region)
    error_message = "Must be a supported region: us-east-1, us-west-2, eu-central-1, or eu-west-1."
  }
}

variable "cluster_name" {
  type        = string
  default     = "virtualcloset-staging"
  description = "Name prefix for all AWS resources."
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

variable "eks_kubernetes_version" {
  type        = string
  default     = "1.30"
  description = "EKS control plane Kubernetes version."
}

variable "node_instance_type" {
  type        = string
  default     = "t3.large"
  description = "EC2 instance type for EKS managed node group."
}

variable "node_desired_size" {
  type        = number
  default     = 2
  description = "Desired number of nodes in the managed node group."
}

variable "node_min_size" {
  type        = number
  default     = 1
  description = "Minimum number of nodes in the managed node group."
}

variable "node_max_size" {
  type        = number
  default     = 3
  description = "Maximum number of nodes in the managed node group."
}

variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed SSH (22) and kubectl (443 to EKS API) access. Use static IPs only."
}

variable "ssh_public_key_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
  description = "Path to SSH public key for node access."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL superuser password. Used to create the backup k8s Secret."
}

variable "backup_retention_days" {
  type        = number
  default     = 30
  description = "Number of days to retain backup files in S3."
}
