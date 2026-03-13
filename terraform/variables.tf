# Region where resources will be created.
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# Used as a tag/name prefix across AWS resources.
variable "project_name" {
  description = "Project name prefix for AWS resources"
  type        = string
  default     = "utility-billing-ai"
}

# Environment label for tags and naming (prod/stage/dev).
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

# Cost-effective default; increase later only if CPU/RAM pressure appears.
variable "instance_type" {
  description = "EC2 instance type (cost-effective default)"
  type        = string
  default     = "t3a.small"
}

# Keep small to reduce cost; increase if Docker images/logs need more disk.
variable "root_volume_size_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}

# Existing EC2 key pair name for SSH access.
variable "ssh_key_name" {
  description = "Existing EC2 key pair name"
  type        = string
}

# Restrict SSH to your public IP (x.x.x.x/32).
variable "ssh_allowed_cidr" {
  description = "CIDR allowed to SSH into instance"
  type        = string
}

# UI access CIDRs for Streamlit; restrict to office/VPN when possible.
variable "streamlit_allowed_cidrs" {
  description = "CIDRs allowed to access Streamlit on port 8501"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Elastic IP helps keep a stable public address.
variable "assign_elastic_ip" {
  description = "Attach an Elastic IP to EC2 instance"
  type        = bool
  default     = true
}

# Phase 2 toggle: install Docker + Compose on first EC2 boot.
variable "enable_docker_bootstrap" {
  description = "Whether to run EC2 user_data that installs Docker and Docker Compose plugin"
  type        = bool
  default     = true
}

# Linux user to add into docker group after install.
variable "ec2_admin_user" {
  description = "EC2 OS user to grant docker group access (Ubuntu AMI default: ubuntu)"
  type        = string
  default     = "ubuntu"
}

# Existing bucket only: Terraform will attach IAM policy, not create a bucket.
variable "existing_s3_bucket_name" {
  description = "Existing S3 bucket name used by the app (no bucket creation in Terraform)"
  type        = string
  default     = ""
}
