variable "cluster_name" {
  type        = string
  description = "Name prefix for VPC resources. Used for EKS tag requirements."
}

variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed SSH (22) inbound access."
}
