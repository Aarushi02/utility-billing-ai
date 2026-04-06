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

Team note:
1. Do not share one PEM file across developers.
2. Use PEM only as break-glass admin access.
3. Primary shared workflow should be IAM + Session Manager.

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
3. `enable_ssm_access = true`
4. `enable_ssh_ingress = true` during migration, then `false` after Session Manager is validated

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

Inside EC2 (bootstrap already installed Docker + 2GB swap on first boot):

```bash
git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git ~/utility-billing-ai
cp ~/.env ~/utility-billing-ai/.env
cd ~/utility-billing-ai
```

Start API + Streamlit + Nginx (production mode with both compose files):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db
```

**Do NOT run `docker compose up` without specifying services** — it would attempt to pull Airflow which exhausts t3.micro RAM.

To start Airflow when needed:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile airflow up -d
```

## 10) Validate Runtime and Exposure

From EC2:

```bash
# API internal health
curl -sS http://127.0.0.1:8000/api/v1/health/live

# Nginx public entry point (port 80)
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:80
```

From laptop/browser:
1. `http://PUBLIC_IP` (port 80) should work — Nginx serves Streamlit
2. `http://PUBLIC_IP:8501` should NOT be reachable — blocked by Security Group
3. `http://PUBLIC_IP:8000` should NOT be reachable
4. `http://PUBLIC_IP:8080` should NOT be reachable

Same IP, same website: the public app URL should be the Elastic IP itself on port 80, for example `http://52.2.3.30`. Streamlit is meant to stay local to the VM and be reached by Nginx only.

## 11) Reuse in Another AWS Account

Usually only these values change:
1. AWS credentials/profile
2. Region
3. Key pair name
4. CIDR allow rules
5. S3 bucket name
6. `.env` app secrets and DB config

Terraform code remains the same.

## 11.1) Multi-Developer Access (No Shared PEM) — Recommended

Use IAM + Session Manager so each developer has their own identity and audit trail.

1. Ensure Terraform enables Session Manager policy on EC2 role:

```hcl
enable_ssm_access = true
```

2. Apply Terraform:

```bash
cd terraform
terraform apply -auto-approve
```

3. Give each developer IAM permissions for Session Manager.
Minimum actions:
1. `ssm:StartSession`
2. `ssm:TerminateSession`
3. `ssm:ResumeSession`
4. `ssm:DescribeSessions`
5. `ssm:GetConnectionStatus`
6. `ec2:DescribeInstances`

Copy-paste least-privilege policy template (replace placeholders first):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DescribeForSessionManager",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ssm:DescribeSessions",
        "ssm:GetConnectionStatus"
      ],
      "Resource": "*"
    },
    {
      "Sid": "StartSessionOnTargetInstance",
      "Effect": "Allow",
      "Action": "ssm:StartSession",
      "Resource": [
        "arn:aws:ec2:<REGION>:<ACCOUNT_ID>:instance/<INSTANCE_ID>",
        "arn:aws:ssm:<REGION>::document/SSM-SessionManagerRunShell",
        "arn:aws:ssm:<REGION>::document/AWS-StartInteractiveCommand"
      ]
    },
    {
      "Sid": "ManageOwnSessionsOnly",
      "Effect": "Allow",
      "Action": [
        "ssm:TerminateSession",
        "ssm:ResumeSession"
      ],
      "Resource": "arn:aws:ssm:<REGION>:<ACCOUNT_ID>:session/${aws:userid}-*"
    }
  ]
}
```

Attach this policy to a developer IAM group (recommended) instead of individual users.
If your session IDs do not match `${aws:userid}-*`, temporarily set `ManageOwnSessionsOnly.Resource` to `*`, validate access, then tighten again.

4. Developers start session from local machine:

```bash
aws ssm start-session --target <INSTANCE_ID> --region us-east-1
```

5. After all developers can connect via SSM, disable SSH ingress:

```hcl
enable_ssh_ingress = false
```

Then apply:

```bash
cd terraform
terraform apply -auto-approve
```

Result:
1. No shared PEM key for day-to-day work
2. Per-user IAM access and revocation
3. Better auditability

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

## 13.1) Simple Security Plan (Do This In Order)

Use this practical order for this project:

Step 1 (now): Tighten Security Group.
1. Keep port `80` open (website stays public).
2. Keep port `22` restricted to one trusted admin IP (or disable later).
3. Keep `8000`, `8501`, `8080` closed.
Why:
1. Website keeps working on the same public IP.
2. Internal services stay private.
3. This is the fastest security improvement with no architecture change.

Step 2 (when ready): Add HTTPS.
1. Move from `http://` to `https://`.
2. Redirect HTTP to HTTPS.
Why:
1. Encrypts user data and passwords in transit.
2. Removes browser "Not Secure" warning.

Step 3 (later, advanced): ALB + private EC2 + NAT.
1. Public ALB receives internet traffic.
2. EC2 runs in private subnet (no public IP).
3. NAT provides outbound internet for private EC2.
Why:
1. Internet cannot hit EC2 directly.
2. Stronger long-term security and scaling model.

Cost note:
1. Step 1 is mostly configuration (lowest cost impact).
2. Step 2 can be low cost (domain and certificate setup effort).
3. Step 3 is stronger but adds AWS recurring cost (ALB/NAT).

## 13.2) Tighten Security Group (Immediate, Practical Now)

Apply this now for your current single-EC2 deployment.

Inbound rules:
1. Allow TCP `80` from `0.0.0.0/0` (public website via Nginx).
2. Allow TCP `22` only from your admin IP `/32` (or disable SSH after SSM migration).
3. Do not allow inbound `8000`, `8501`, `8080`.

Outbound rules:
1. Keep default allow-all outbound for now.

Terraform mapping in this repo:
1. `ssh_allowed_cidr` controls SSH source.
2. `enable_ssh_ingress` toggles SSH rule on/off.
3. Security Group intentionally exposes `80` only for app traffic.

Validation commands:
```bash
# Public app must respond on 80
curl -sS -o /dev/null -w "%{http_code}\n" http://PUBLIC_IP

# These must not be publicly reachable
curl -sS -o /dev/null -w "%{http_code}\n" http://PUBLIC_IP:8501 --connect-timeout 8 || true
curl -sS -o /dev/null -w "%{http_code}\n" http://PUBLIC_IP:8000 --connect-timeout 8 || true
```

Expected:
1. Port `80` returns `200`.
2. Ports `8501` and `8000` time out or fail.

## 13.3) Additional Security Checklist (Practical)

Use this checklist after Step 1/Step 2 are stable.

Secrets and credentials:
1. Never commit `.env`, PEM keys, DB passwords, API keys, or tokens to git.
2. Rotate DB and API credentials periodically.
3. Prefer IAM role access on EC2 over long-lived static AWS keys.

Server hardening:
1. Keep OS security updates current.
2. Keep Docker engine and images updated.
3. Remove/disable unused services and unused public ports.
4. Keep Airflow profile off unless needed for active work.
5. Keep IAM permissions least-privilege.

Monitoring and alerting:
1. Add a basic uptime check for the public URL.
2. Add EC2 alerts for stop/failure/high CPU.
3. Review application logs regularly, especially failed login/auth patterns.

Web-layer protections (gradual):
1. Add Nginx rate limiting for login/API-sensitive endpoints.
2. Add security headers (for example HSTS, X-Frame-Options, and related browser protections).
3. If SSH remains enabled, optionally add fail2ban for brute-force protection.

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
[ ] App public URL works at http://PUBLIC_IP (port 80 via Nginx)
[ ] API port 8000 not publicly exposed
[ ] Streamlit port 8501 not publicly exposed (Nginx handles it)
[ ] Airflow port 8080 not publicly exposed
[ ] Swap space present: `free -h` shows Swap: 2.0Gi

## 15) Update Log (Keep This Section Growing)

Use this section to append future steps without deleting old decisions.

Template:
1. Date:
2. Change made:
3. Why:
4. Commands used:
5. Validation done:

### 2026-03-18 (Session 2 — Nginx + Swap + Full Redeploy)

1. Change made:
- Added 2GB swap to EC2 bootstrap script (prevents t3.micro OOM crash under Docker load)
- Added Nginx reverse proxy — Streamlit no longer directly public; Nginx on port 80 handles all traffic
- Fixed `proxy_pass` in `nginx.conf` to use Docker service name `http://streamlit:8501` (not `127.0.0.1`)
- Disabled Airflow via Docker Compose `profiles: [airflow]` — prevents accidental Airflow image pull
- Security Group updated: port 80 open (Nginx), port 8501 removed
- Terraform destroy + rebuild: new EC2 (`i-06ebc19f707862bdd`), new IP (`52.2.3.30`)
- Full deployment: clone → .env → docker compose up (api + streamlit + nginx) → init_db

2. Why:
- Previous EC2 froze due to RAM exhaustion — no swap + Airflow image pull
- Streamlit on port 8501 was publicly accessible — Nginx adds security layer
- `127.0.0.1` in nginx.conf referred to Nginx container itself, not Streamlit

3. Commands used:
```bash
# Terraform rebuild
cd terraform
terraform destroy -auto-approve
terraform apply -auto-approve

# Copy .env to new EC2
scp -i ~/Desktop/utility-billing-key.pem .env ubuntu@52.2.3.30:~/.env

# Deploy on EC2
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@52.2.3.30
git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git ~/utility-billing-ai
cp ~/.env ~/utility-billing-ai/.env
cd ~/utility-billing-ai
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db
```

4. Validation done:
- `free -h` shows Swap: 2.0Gi ✅
- Docker 29.3.0 installed ✅
- All 3 containers Up and healthy ✅
- API health: `{"status":"ok"}` ✅
- Nginx HTTP status: 200 ✅
- App live at `http://52.2.3.30` ✅

### 2026-03-13 (Session 1 — Initial Setup)

1. Change made:
- Provisioned Terraform infra successfully (EC2, SG, IAM role/profile, EIP).
- Enabled EC2 Docker bootstrap via user_data.
- Synced local workspace code to EC2.
- Switched preferred app startup to `api + streamlit` only for now.

2. Why:
- Keep deployment simple and aligned with current scope (no Airflow runtime required now).

3. Commands used:
- Infra create:
```bash
cd terraform
terraform init
terraform plan
terraform apply -auto-approve
```
- Code transfer:
```bash
# initial env copy
scp -i ~/Desktop/utility-billing-key.pem .env ubuntu@<PUBLIC_IP>:/home/ubuntu/utility-billing-ai/.env

# full workspace sync to ensure remote matches local
rsync -az --delete \
  --exclude '.git' --exclude 'venv' --exclude '__pycache__' --exclude '.DS_Store' \
  --exclude 'logs/' --exclude 'data/raw/' --exclude 'data/samples/' \
  -e "ssh -i ~/Desktop/utility-billing-key.pem" \
  /path/to/local/utility-billing-ai/ \
  ubuntu@<PUBLIC_IP>:/home/ubuntu/utility-billing-ai/
```

4. Validation done:
- EC2 AWS status checks: `running`, `system ok`, `instance ok`.
- Security group verified: SSH and 8501 present.

5. Current issue:
- SSH timed out during banner exchange after large remote build logs.
- Public 8501 check also timed out.

6. Recovery next commands:
```bash
# reboot instance to recover ssh daemon/network stack if needed
aws ec2 reboot-instances --region us-east-1 --instance-ids <INSTANCE_ID>

# after 60-120s
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@<PUBLIC_IP>
cd ~/utility-billing-ai
docker compose up -d --build api streamlit
docker compose exec -T api python -m src.database.init_db
docker compose ps
```
