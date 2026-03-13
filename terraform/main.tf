# AWS provider configuration.
provider "aws" {
  region = var.aws_region
}

# Optional Phase 2 bootstrap payload (Docker install only).
locals {
  docker_bootstrap_user_data = templatefile("${path.module}/scripts/bootstrap_docker.sh.tftpl", {
    ec2_admin_user = var.ec2_admin_user
  })
}

# Reuse default VPC for lowest-complexity/lowest-cost start.
data "aws_vpc" "default" {
  default = true
}

# Get subnets inside default VPC; first subnet is used for EC2.
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Fetch latest Ubuntu LTS AMI from Canonical.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for a single EC2 deployment host.
resource "aws_security_group" "app" {
  name        = "${var.project_name}-${var.environment}-sg"
  description = "Security group for Utility Billing AI app server"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from admin network"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  ingress {
    description = "Streamlit UI"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = var.streamlit_allowed_cidrs
  }

  # Intentionally no ingress rules for 8000 (API) and 8080 (Airflow).
  # Those services stay private and only listen on localhost in docker-compose.

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Role assumed by EC2 to access AWS services (for example existing S3 bucket).
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach least-privilege bucket access only when bucket name is provided.
resource "aws_iam_role_policy" "existing_bucket_access" {
  count = var.existing_s3_bucket_name != "" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-existing-bucket-access"
  role  = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.existing_s3_bucket_name}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.existing_s3_bucket_name}/*"
        ]
      }
    ]
  })
}

# Bridge IAM role to EC2 via instance profile.
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# Single application host for Docker Compose workloads.
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name
  subnet_id              = element(data.aws_subnets.default.ids, 0)
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  # Phase 2: install Docker and Docker Compose plugin automatically on first boot.
  user_data              = var.enable_docker_bootstrap ? local.docker_bootstrap_user_data : null

  root_block_device {
    # gp3 is cost-effective and performs well for this workload.
    volume_type = "gp3"
    volume_size = var.root_volume_size_gb
  }

  metadata_options {
    # Require IMDSv2 for stronger metadata service security.
    http_tokens = "required"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Optional stable public IP for easier DNS/operations.
resource "aws_eip" "app" {
  count    = var.assign_elastic_ip ? 1 : 0
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-${var.environment}-eip"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Optional future S3 creation (intentionally commented out).
# You already have an S3 bucket and should keep using it.
# resource "aws_s3_bucket" "app_bucket" {
#   bucket = "${var.project_name}-${var.environment}-bucket"
#
#   tags = {
#     Name        = "${var.project_name}-${var.environment}-bucket"
#     Project     = var.project_name
#     Environment = var.environment
#   }
# }
