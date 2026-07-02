variable "cluster_name" {
  type        = string
  description = "EKS cluster name."
}

variable "aws_region" {
  type        = string
  description = "AWS region."
}

variable "eks_kubernetes_version" {
  type        = string
  description = "EKS Kubernetes version (e.g. 1.30)."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID from the vpc module."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for node group placement."
}

variable "node_instance_type" {
  type        = string
  description = "EC2 instance type for managed node group."
}

variable "node_desired_size" {
  type        = number
  description = "Desired number of nodes."
}

variable "node_min_size" {
  type        = number
  description = "Minimum number of nodes."
}

variable "node_max_size" {
  type        = number
  description = "Maximum number of nodes."
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to SSH public key for node access."
}

variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed to reach the EKS API server endpoint."
}

variable "node_security_group_id" {
  type        = string
  description = "Security group ID for EKS worker nodes."
}
