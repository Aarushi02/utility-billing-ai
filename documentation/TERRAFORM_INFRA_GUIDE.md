# Terraform Infrastructure Guide

Primary consolidated cloud setup guide: [documentation/AWS_REUSE_SETUP_RUNBOOK.md](documentation/AWS_REUSE_SETUP_RUNBOOK.md)

Note: this file is retained for historical context. The runbook above should be treated as the single source of truth going forward.

This document explains:

1. What has already been set up
2. How Terraform flow works in this project
3. How to connect your machine to AWS for Terraform
4. What "Phase 2 bootstrap" means
5. Future step-by-step workflow

## 1) What We Have Done Already

Terraform files were added under `terraform/` with a cost-effective infrastructure-first scope.

Current resources defined:

1. One EC2 instance (single Docker host)
2. One Security Group
3. One IAM role + instance profile attached to EC2
4. Optional Elastic IP
5. Optional IAM policy to access your existing S3 bucket
6. Optional EC2 first-boot Docker bootstrap via `user_data`

Current resources intentionally NOT created:

1. New S3 bucket (because you already have one)
2. Load balancer, NAT gateway, ECS, autoscaling (to keep cost low)
3. DNS/HTTPS resources (can be added later)

## 2) How This Terraform Works

Terraform compares desired state (your `.tf` files) with real AWS state, then applies changes.

Basic command flow:

1. `terraform init`
: downloads AWS provider plugin
2. `terraform plan`
: shows what will be created/changed (no changes yet)
3. `terraform apply`
: creates resources in AWS
4. `terraform destroy`
: deletes resources when no longer needed

Important behavior:

1. Running `plan/apply` repeatedly is safe; Terraform is declarative and idempotent.
2. State is stored locally by default (`terraform.tfstate`) in this setup.
3. `.gitignore` now excludes Terraform state and local tfvars.

## 3) How To Connect To AWS First Time

You have two common options.

### Option A: Access Keys (simplest to start)

1. In AWS Console, create an IAM user (or use existing one) with programmatic access.
2. Attach least-privilege permissions for EC2/IAM/EIP/SG actions used by this stack.
3. Install AWS CLI locally.
4. Run:

```bash
aws configure
```

5. Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (`us-east-1`)
- Output format (`json`)

6. Verify:

```bash
aws sts get-caller-identity
```

If this returns your account/user ARN, Terraform can authenticate.

### Required IAM permissions for this Terraform stack

Your IAM principal must allow at least the following actions (or broader equivalent):

1. EC2 read/create/manage:
- `ec2:DescribeVpcs`
- `ec2:DescribeSubnets`
- `ec2:DescribeImages`
- `ec2:DescribeSecurityGroups`
- `ec2:CreateSecurityGroup`
- `ec2:AuthorizeSecurityGroupIngress`
- `ec2:AuthorizeSecurityGroupEgress`
- `ec2:CreateTags`
- `ec2:RunInstances`
- `ec2:DescribeInstances`
- `ec2:AllocateAddress`
- `ec2:AssociateAddress`

2. IAM for instance role/profile:
- `iam:CreateRole`
- `iam:PutRolePolicy`
- `iam:CreateInstanceProfile`
- `iam:AddRoleToInstanceProfile`
- `iam:GetRole`
- `iam:GetInstanceProfile`
- `iam:PassRole`

If these are missing, `terraform plan/apply` will fail with `UnauthorizedOperation` even when login succeeds.

### Option B: AWS SSO (recommended for teams)

1. Configure SSO profile in AWS CLI.
2. Login:

```bash
aws sso login --profile <profile-name>
```

3. Run Terraform with profile:

```bash
AWS_PROFILE=<profile-name> terraform plan
```

## 4) What Is "Phase 2 Bootstrap (Docker install only)?"

Phase 1 (already done): Provision infrastructure.

Phase 2 (now implemented): Minimal instance bootstrap automation using `user_data` to install runtime dependencies on EC2:

1. Docker Engine
2. Docker Compose plugin
3. Basic system packages (git, curl)

Where it is configured:

1. `terraform/main.tf` (`user_data` wiring)
2. `terraform/scripts/bootstrap_docker.sh.tftpl` (bootstrap script)
3. `terraform/variables.tf` (`enable_docker_bootstrap`, `ec2_admin_user`)

What Phase 2 does NOT do yet:

1. It does not deploy your app containers automatically
2. It does not write your `.env` secrets
3. It does not run `docker compose up`

Why keep this separate:

1. Cleaner troubleshooting (infra issues vs app issues)
2. Safer iterations
3. Easy rollback if bootstrap script fails

## 5) Step-By-Step Future Workflow

### Phase 1: Infrastructure

1. Install Terraform
2. Copy vars file:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

3. Edit `terraform.tfvars` values:
- `ssh_key_name`
- `ssh_allowed_cidr`
- `existing_s3_bucket_name`

4. Deploy infra:

```bash
terraform init
terraform plan
terraform apply
```

5. Save outputs (public IP, ssh command)

### Phase 2: Bootstrap (optional, next)

1. Keep `enable_docker_bootstrap=true` in `terraform.tfvars`
2. Run `terraform plan` and `terraform apply`
3. SSH into EC2 and verify:

```bash
docker --version
docker compose version
sudo cat /var/log/docker-bootstrap.done
```

### Phase 3: Application deployment

1. SSH to EC2
2. Clone repo
3. Create `.env`
4. Run:

```bash
docker compose up -d --build api streamlit airflow
```

5. Initialize DB:

```bash
docker compose exec api python -m src.database.init_db
```

6. Verify:
- `http://<PUBLIC_IP>:8501` reachable
- `:8000` and `:8080` not publicly reachable

## 6) Cost-Effective Design Notes

1. Single EC2 host keeps monthly cost low.
2. No ALB/NAT/ECS yet avoids common baseline AWS overhead.
3. Start with `t3a.small`; move up only if metrics show need.
4. Restrict `ssh_allowed_cidr` to your IP.
5. Later, if traffic increases, add ALB + HTTPS + autoscaling in controlled steps.
