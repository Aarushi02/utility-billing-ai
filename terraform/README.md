# Terraform Infrastructure Guide (What Is Set Up Here)

Primary cloud guide: [documentation/AWS_REUSE_SETUP_RUNBOOK.md](documentation/AWS_REUSE_SETUP_RUNBOOK.md)
Historical Terraform notes: [documentation/TERRAFORM_INFRA_GUIDE.md](documentation/TERRAFORM_INFRA_GUIDE.md)

This folder contains the infrastructure-as-code for a low-cost AWS deployment.

What it creates:
1. One EC2 instance for the app host
2. One Security Group
3. One IAM role and one IAM instance profile
4. One Elastic IP (optional)
5. Optional IAM policy for an existing S3 bucket
6. Optional first-boot Docker bootstrap on EC2

What it intentionally does not create:
1. New S3 bucket
2. ALB, NAT Gateway, ECS, autoscaling
3. DNS/HTTPS stack

## File-by-File Breakdown

1. [terraform/versions.tf](versions.tf)
- Pins Terraform and AWS provider versions.
- Keeps builds reproducible across machines.

2. [terraform/variables.tf](variables.tf)
- Declares all configurable inputs.
- Examples: region, instance type, SSH CIDR, key pair name, S3 bucket name, bootstrap toggle.

3. [terraform/main.tf](main.tf)
- Core infrastructure definition.
- Provider setup.
- Data sources:
	1. Default VPC
	2. Subnets in that VPC
	3. Latest Ubuntu AMI
- Resources:
	1. Security Group
	2. IAM role
	3. IAM inline policy for existing S3 bucket access
	4. IAM instance profile
	5. EC2 instance
	6. Elastic IP (optional)
- Bootstrap wiring:
	1. Reads the bootstrap script template
	2. Injects it into EC2 user_data when enabled

4. [terraform/outputs.tf](outputs.tf)
- Prints useful values after apply.
- Outputs include instance ID, public IP, security group ID, and SSH command.

5. [terraform/terraform.tfvars.example](terraform.tfvars.example)
- Sample values for quick setup.
- Copy this to terraform.tfvars and set real values.

6. [terraform/terraform.tfvars](terraform.tfvars)
- Your active local values for this environment/account.
- Ignored from git for safety.

7. [terraform/scripts/bootstrap_docker.sh.tftpl](scripts/bootstrap_docker.sh.tftpl)
- First-boot EC2 script template.
- Installs Docker Engine and Docker Compose plugin.
- Enables and starts Docker service.
- Adds configured admin user to docker group.
- Writes a verification marker file in /var/log/docker-bootstrap.done.

## How main.tf Works

Execution flow:
1. Terraform reads variables from [terraform/terraform.tfvars](terraform.tfvars).
2. Finds default VPC, subnet, and Ubuntu AMI.
3. Creates security boundary (Security Group).
4. Creates IAM role/profile for EC2 access to AWS services.
5. Creates EC2 instance with optional user_data bootstrap.
6. Allocates and associates Elastic IP when enabled.
7. Prints outputs.

## Security Choices in This Setup

1. SSH only from configured CIDR on port 22.
2. Streamlit exposed on port 8501.
3. API and Airflow are kept private by compose localhost binding.
4. IMDSv2 is enforced on EC2 metadata service.

## Cost Choices in This Setup

1. Single-VM architecture (EC2 only).
2. Default VPC reuse.
3. Small instance type by default.
4. No always-on extra managed services.

## Quick Commands

Initialize and apply:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars
terraform init
terraform plan
terraform apply -auto-approve
```

Destroy:

```bash
cd terraform
terraform destroy -auto-approve
```

## Operational Notes

1. If user_data changes are not reflected, run a new apply and verify instance recreation policy for your changes.
2. If permissions fail with UnauthorizedOperation, fix IAM policy and rerun plan.
3. If key pair errors appear, verify key name exists in the target AWS region.
