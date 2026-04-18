# Disaster Recovery Runbook — EC2/EIP Deleted Outside Terraform

Use this when someone manually deleted the EC2 or Elastic IP, Terraform state is stale,
and you need to rebuild everything cleanly.

---

## Situation

Symptoms:
- App at `http://<IP>` is unreachable
- `terraform output` shows an old instance ID that no longer exists in AWS
- AWS console shows a different instance than what Terraform tracks
- Two instances or two Elastic IPs with the same name exist

---

## Step 1 — Find what actually exists in AWS

```bash
# Check both regions — instance may have drifted to wrong region
AWS_DEFAULT_REGION=us-east-1 aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,Tags[?Key=='Name'].Value|[0]]" \
  --output table

AWS_DEFAULT_REGION=us-east-2 aws ec2 describe-instances \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress,Tags[?Key=='Name'].Value|[0]]" \
  --output table

# Check Elastic IPs
AWS_DEFAULT_REGION=us-east-2 aws ec2 describe-addresses \
  --query "Addresses[*].[PublicIp,AllocationId,InstanceId]" --output table
```

---

## Step 2 — Fix region in terraform.tfvars if needed

If the actual instance is in a different region than Terraform expects:

```bash
# Edit terraform/terraform.tfvars
aws_region = "us-east-2"   # match where resources actually exist

# Edit terraform/variables.tf default to match too
default = "us-east-2"
```

---

## Step 3 — Import surviving resources into Terraform state

Any resource that still exists in AWS but not in Terraform state must be imported.
Run only the ones that already exist:

```bash
cd terraform

# Security Group
terraform import aws_security_group.app <sg-id>

# Lambda functions
terraform import "aws_lambda_function.ec2_start[0]" utility-billing-ai-prod-ec2-start
terraform import "aws_lambda_function.ec2_stop[0]" utility-billing-ai-prod-ec2-stop

# EventBridge schedules
terraform import "aws_scheduler_schedule.ec2_start[0]" default/utility-billing-ai-prod-ec2-start
terraform import "aws_scheduler_schedule.ec2_stop[0]" default/utility-billing-ai-prod-ec2-stop
```

---

## Step 4 — Apply to recreate missing resources

```bash
cd terraform
terraform init -reconfigure
terraform apply -auto-approve
```

Get the new Elastic IP:

```bash
terraform output instance_public_ip
terraform output instance_id
```

---

## Step 5 — Wait for Docker bootstrap to complete

The bootstrap script runs automatically on first boot (installs Docker + 2GB swap).
Wait ~2 minutes then verify via SSM:

```bash
AWS_DEFAULT_REGION=us-east-2 aws ssm send-command \
  --instance-ids <instance-id> \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cat /var/log/docker-bootstrap.done", "docker --version"]' \
  --query "Command.CommandId" --output text
```

Expected output: `Docker bootstrap completed at ...`

---

## Step 6 — Push .env to EC2 via SSM

```bash
# Base64-encode local .env and write it to EC2
ENV_B64=$(base64 -i .env | tr -d '\n')

AWS_DEFAULT_REGION=us-east-2 aws ssm send-command \
  --instance-ids <instance-id> \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"echo '$ENV_B64' | base64 -d > /home/ubuntu/utility-billing-ai/.env\"]" \
  --query "Command.CommandId" --output text
```

Note: if `.env` has variable names with special characters like `&`, comment them out first
(Docker Compose cannot parse `&` in variable names):

```bash
sed -i "s/^OPENAI_API_KEY_T&B=/#OPENAI_API_KEY_T&B=/g" .env
sed -i "s/^General_Purpose_API_T&B =/#General_Purpose_API_T&B =/g" .env
```

---

## Step 7 — Clone repo and deploy app

```bash
AWS_DEFAULT_REGION=us-east-2 aws ssm send-command \
  --instance-ids <instance-id> \
  --document-name "AWS-RunShellScript" \
  --timeout-seconds 600 \
  --parameters 'commands=[
    "git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git ~/utility-billing-ai || (cd ~/utility-billing-ai && git pull origin Dev)",
    "cp ~/.env ~/utility-billing-ai/.env",
    "cd ~/utility-billing-ai && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx",
    "docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db",
    "docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
  ]'
```

---

## Step 8 — Update IP in all docs

```bash
# Replace old IP with new IP across all documentation
OLD_IP="<old-ip>"
NEW_IP="<new-ip>"

sed -i '' "s/$OLD_IP/$NEW_IP/g" \
  README.md \
  RUNBOOK_DEPLOYMENT.md \
  documentation/DEPLOYMENT.md \
  documentation/AWS_REUSE_SETUP_RUNBOOK.md \
  documentation/DEPLOYMENT_PROGRESS_CHECKLIST.md \
  documentation/DISASTER_RECOVERY_RUNBOOK.md
```

---

## Step 9 — Clean up orphan resources

If there are old instances or Elastic IPs still running:

```bash
# Terminate old instance
aws ec2 terminate-instances --instance-ids <old-instance-id>

# Release old Elastic IP (disassociate first if still attached)
aws ec2 disassociate-address --association-id <assoc-id>
aws ec2 release-address --allocation-id <alloc-id>
```

---

## Step 10 — Verify

```bash
# From browser
http://<NEW_IP>   # should load Streamlit app via Nginx

# From EC2 via SSM
curl -sS http://127.0.0.1:8000/api/v1/health/live   # should return {"status":"ok"}
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:80   # should return 200
```

---

## Quick Reference — Current Production Values

| Resource | Value |
|---|---|
| Region | `us-east-2` |
| Instance ID | `i-0393dd4f827866db2` |
| Elastic IP | `3.12.193.9` |
| App URL | `http://3.12.193.9` |
| EC2 Name | `utility-billing-ai-prod-ec2` |
| Key Pair | `utility-billing-key` |
| S3 Bucket | `utility-billing-storage` (us-east-1) |
