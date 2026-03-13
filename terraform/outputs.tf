# Useful values printed after terraform apply.
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "instance_public_ip" {
  description = "Public IP address of EC2 instance (Elastic IP if assigned)"
  value       = var.assign_elastic_ip ? aws_eip.app[0].public_ip : aws_instance.app.public_ip
}

output "security_group_id" {
  description = "Security group ID for the app server"
  value       = aws_security_group.app.id
}

output "ssh_command" {
  description = "SSH command template"
  value       = "ssh ubuntu@${var.assign_elastic_ip ? aws_eip.app[0].public_ip : aws_instance.app.public_ip}"
}
