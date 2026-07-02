output "vpc_id" {
  description = "AWS VPC ID."
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for EKS node group placement."
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for load balancers."
  value       = aws_subnet.public[*].id
}

output "node_security_group_id" {
  description = "Security group ID attached to EKS nodes."
  value       = aws_security_group.node.id
}
