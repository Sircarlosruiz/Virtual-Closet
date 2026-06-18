variable "cluster_name" {
  type        = string
  description = "Name prefix for VPC resources."
}

variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed SSH (22) and kubectl API (6443) inbound access."
}
