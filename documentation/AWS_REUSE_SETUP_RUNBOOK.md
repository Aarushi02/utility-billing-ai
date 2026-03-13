# AWS Cloud Setup Runbook (Primary Guide)

This is the single source of truth for repeating the same setup in any AWS account with different configuration values.

Use this for:
1. Fresh account setup
2. Reusing the same codebase with different `.env` and Terraform values
3. End-to-end infra + bootstrap + app deployment
4. Ongoing updates as next steps evolve

## 0) Architecture and Scope

Current design (cost-effective first):
1. One EC2 instance for app runtime
2. One Security Group
3. One IAM role + instance profile attached to EC2
4. One Elastic IP (optional but enabled)
5. Optional IAM policy for existing S3 bucket access
6. Optional first-boot Docker bootstrap via EC2 `user_data`

Not created intentionally:
1. New S3 bucket (reuse existing)
2. ALB, NAT Gateway, ECS, autoscaling
3. DNS/HTTPS stack (can be added later)

## 1) Prerequisites

1. macOS terminal access
2. Repo cloned locally
3. AWS account access
4. IAM rights to create EC2/IAM/EIP/SG resources

## 2) Install Tools

Run:

```bash
brew install awscli terraform
```

Verify:

```bash
aws --version
terraform version
```

## 3) Connect AWS in Terminal

Option A (access keys):

```bash
aws configure
aws sts get-caller-identity
```

Enter:
1. AWS Access Key ID
2. AWS Secret Access Key
3. Default region (example `us-east-1`)
4. Output format `json`

Option B (SSO):

```bash
aws sso login --profile YOUR_PROFILE
AWS_PROFILE=YOUR_PROFILE aws sts get-caller-identity
```

## 4) Required IAM Permissions

Minimal actions needed for this Terraform stack:

EC2:
1. `ec2:DescribeVpcs`
2. `ec2:DescribeSubnets`
3. `ec2:DescribeImages`
4. `ec2:DescribeSecurityGroups`
5. `ec2:CreateSecurityGroup`
6. `ec2:AuthorizeSecurityGroupIngress`
7. `ec2:AuthorizeSecurityGroupEgress`
8. `ec2:CreateTags`
9. `ec2:RunInstances`
10. `ec2:DescribeInstances`
11. `ec2:AllocateAddress`
12. `ec2:AssociateAddress`
13. `ec2:DescribeKeyPairs`
14. `ec2:CreateKeyPair`

IAM:
1. `iam:CreateRole`
2. `iam:PutRolePolicy`
3. `iam:CreateInstanceProfile`
4. `iam:AddRoleToInstanceProfile`
5. `iam:GetRole`
6. `iam:GetInstanceProfile`
7. `iam:PassRole`

Fast unblock policies during setup:
1. `AmazonEC2FullAccess`
2. `IAMFullAccess`
3. `AmazonS3FullAccess` (or narrower bucket policy)

## 5) Create EC2 SSH Key Pair

Create and save local pem:

```bash
aws ec2 create-key-pair \
  --key-name utility-billing-key \
  --region us-east-1 \
  --query KeyMaterial \
  --output text > ~/Desktop/utility-billing-key.pem

chmod 400 ~/Desktop/utility-billing-key.pem
```

Verify:

```bash
aws ec2 describe-key-pairs --region us-east-1 --query 'KeyPairs[].KeyName' --output text
```

## 6) Configure Terraform Variables

Main file: [terraform/terraform.tfvars](terraform/terraform.tfvars)

Update at minimum:
1. `aws_region`
2. `ssh_key_name`
3. `ssh_allowed_cidr`
4. `existing_s3_bucket_name`
5. `instance_type` (cost default: `t3.micro`)

Get your public IP:

```bash
curl -s https://checkip.amazonaws.com
```

Set:
1. `ssh_allowed_cidr = YOUR_IP/32`
2. `streamlit_allowed_cidrs = ["0.0.0.0/0"]` during initial testing

## 7) Phase 1: Create Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply -auto-approve
```

Expected outputs:
1. `instance_id`
2. `instance_public_ip`
3. `security_group_id`
4. `ssh_command`

## 8) Phase 2: Bootstrap Verification (Docker install only)

Bootstrap is controlled by:
1. `enable_docker_bootstrap`
2. `ec2_admin_user`

Configured in:
1. [terraform/main.tf](terraform/main.tf)
2. [terraform/scripts/bootstrap_docker.sh.tftpl](terraform/scripts/bootstrap_docker.sh.tftpl)
3. [terraform/variables.tf](terraform/variables.tf)

SSH and verify:

```bash
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@PUBLIC_IP
docker --version
docker compose version
sudo cat /var/log/docker-bootstrap.done
```

Note: wait 30 to 90 seconds after first boot before validating.

## 9) Phase 3: Deploy Application on EC2

Inside EC2:

```bash
sudo apt update -y
sudo apt install -y git
git clone YOUR_REPO_URL
cd utility-billing-ai
```

Create `.env` with environment-specific values, then run:

```bash
docker compose up -d --build api streamlit airflow
docker compose exec api python -m src.database.init_db
```

## 10) Validate Runtime and Exposure

From EC2:

```bash
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080
```

From laptop/browser:
1. `http://PUBLIC_IP:8501` should work
2. `http://PUBLIC_IP:8000` should not be publicly reachable
3. `http://PUBLIC_IP:8080` should not be publicly reachable

## 11) Reuse in Another AWS Account

Usually only these values change:
1. AWS credentials/profile
2. Region
3. Key pair name
4. CIDR allow rules
5. S3 bucket name
6. `.env` app secrets and DB config

Terraform code remains the same.

## 12) Cleanup

Destroy infra:

```bash
cd terraform
terraform destroy -auto-approve
```

Optional key cleanup:
1. Delete key pair from AWS console
2. Remove local pem file

## 13) Cost Notes

1. Single EC2 keeps baseline low.
2. Avoiding ALB/NAT/ECS reduces fixed monthly overhead.
3. `t3.micro` is a good low-cost starting point.
4. Tighten `ssh_allowed_cidr` to reduce risk.
5. Add ALB/HTTPS/autoscaling later only when required.

## 14) Run Checklist

Account and tools:
[ ] awscli installed
[ ] terraform installed
[ ] `aws sts get-caller-identity` works

Permissions:
[ ] IAM principal has required EC2/IAM permissions

SSH and vars:
[ ] EC2 key pair created
[ ] local pem saved and `chmod 400`
[ ] `terraform.tfvars` updated (region, key, cidr, bucket)

Infra:
[ ] `terraform init` successful
[ ] `terraform plan` successful
[ ] `terraform apply` successful

Server bootstrap:
[ ] SSH works
[ ] `docker --version` works
[ ] `/var/log/docker-bootstrap.done` exists

App deployment:
[ ] repo cloned on EC2
[ ] `.env` configured
[ ] `docker compose up` successful
[ ] `init_db` command successful

Validation:
[ ] Streamlit public URL works on port 8501
[ ] API port 8000 not publicly exposed
[ ] Airflow port 8080 not publicly exposed

## 15) Update Log (Keep This Section Growing)

Use this section to append future steps without deleting old decisions.

Template:
1. Date:
2. Change made:
3. Why:
4. Commands used:
5. Validation done:
