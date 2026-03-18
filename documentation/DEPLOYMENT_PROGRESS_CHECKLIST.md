# Deployment Progress Checklist (Current Session)

This checklist tracks exactly what has been completed so far and what is still pending.

## A) Completed Steps (In Order)

1. Terraform and AWS CLI setup
- [x] Installed `awscli` locally
- [x] Installed `terraform` locally
- [x] Verified credentials with `aws sts get-caller-identity`

2. Terraform infra foundation
- [x] Created Terraform folder and files
- [x] Added comments and documentation for Terraform files
- [x] Added cost-effective defaults and variableized config
- [x] Added bootstrap script for Docker on EC2 first boot

3. Infrastructure provisioning
- [x] Ran `terraform init`
- [x] Ran `terraform plan`
- [x] Ran `terraform apply`
- [x] Created EC2 instance
- [x] Created Security Group
- [x] Created IAM role + policy + instance profile
- [x] Created and attached Elastic IP

4. SSH and key management
- [x] Created EC2 key pair in AWS
- [x] Saved PEM locally and set correct permissions (`chmod 400`)

5. Code and config transfer to EC2
- [x] Cloned repo on EC2
- [x] Synced local workspace to EC2 using `rsync`
- [x] Copied `.env` to EC2

6. Deployment behavior decision
- [x] Decided to run only backend + streamlit for now (no Airflow runtime)
- [x] Updated runbook command path accordingly

7. Documentation completed
- [x] Primary cloud runbook consolidated
- [x] Terraform README expanded with file-by-file explanation
- [x] Session update log appended to runbook

## B) Current State / Blocker

1. Infra health
- [x] EC2 state = `running`
- [x] System status checks = `ok`
- [x] Instance status checks = `ok`

2. Connectivity issue
- [ ] SSH currently timing out (`Connection timed out during banner exchange`)
- [ ] Public Streamlit port check currently timing out (`http://<IP>:8501`)

3. Security rule status
- [x] Port 22 rule exists (including temporary open rule added for troubleshooting)
- [x] Port 8501 rule exists

## C) Pending Next Steps (Action Checklist)

### Immediate Recovery

1. Reboot EC2 once
- [ ] Run:
  `aws ec2 reboot-instances --region us-east-1 --instance-ids i-0f8cf5fb0b2591208`

2. Wait and retry SSH
- [ ] Wait 60 to 120 seconds
- [ ] Test:
  `ssh -i ~/Desktop/utility-billing-key.pem ubuntu@34.197.15.20 "echo connected && uptime"`

### App Bring-Up (API + Streamlit only)

3. Start app services
- [ ] SSH into EC2
- [ ] `cd ~/utility-billing-ai`
- [ ] `docker compose down --remove-orphans`
- [ ] `docker compose up -d --build api streamlit`

4. Initialize DB
- [ ] `docker compose exec -T api python -m src.database.init_db`

5. Verify runtime
- [ ] `docker compose ps`
- [ ] `curl -sS http://127.0.0.1:8000/api/v1/health/live`
- [ ] `curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501`

6. Verify public access
- [ ] Open `http://34.197.15.20:8501`

### Security Cleanup (After service is stable)

7. Remove temporary SSH open-to-world rule
- [ ] Remove temporary `0.0.0.0/0` rule for port 22
- [ ] Keep only your fixed admin IP CIDR

## D) Optional Next Phase (Later)

1. Airflow runtime
- [ ] Add Airflow service startup only when needed

2. Hardening
- [ ] Restrict Streamlit CIDR if needed
- [ ] Add reverse proxy + HTTPS (domain path)

3. Operations
- [ ] Add backup/monitoring and routine update process

## E) Quick Commands Bundle

```bash
# 1) Reboot
aws ec2 reboot-instances --region us-east-1 --instance-ids i-0f8cf5fb0b2591208

# 2) SSH test
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@34.197.15.20 "echo connected && uptime"

# 3) App start (on EC2)
cd ~/utility-billing-ai
docker compose down --remove-orphans
docker compose up -d --build api streamlit
docker compose exec -T api python -m src.database.init_db
docker compose ps

# 4) Health checks (on EC2)
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
```
