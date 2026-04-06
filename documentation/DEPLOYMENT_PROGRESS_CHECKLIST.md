# AWS Cloud Deployment — Progress Checklist
**Project:** Utility Billing AI
**Server:** AWS EC2 t3.micro — `us-east-1`
**Last Updated:** 2026-03-19
**Current Public IP:** `52.2.3.30`
**App URL:** `http://52.2.3.30` *(via Nginx on port 80)*

> **IP NOTE:** Elastic IP is released when `terraform destroy` runs. AWS assigns a new one on next `terraform apply`.
> To avoid IP change: never destroy — only stop the EC2 instance.

---

## ✅ COMPLETED

### 1. Local Tooling Setup
- [x] Installed `awscli` locally
- [x] Installed `terraform` locally
- [x] Verified AWS credentials with `aws sts get-caller-identity`

---

### 2. Terraform Infrastructure (IaC — fully reproducible)
- [x] `terraform/main.tf` — EC2, Security Group, Elastic IP, IAM role/policy/profile
- [x] `terraform/variables.tf` — all values parameterized (instance type, region, admin IP, key name)
- [x] `terraform/outputs.tf` — prints instance ID, public IP, SSH command after apply
- [x] `terraform/terraform.tfvars` — actual values (NOT committed — in `.gitignore`)
- [x] `terraform/scripts/bootstrap_docker.sh.tftpl` — runs on EC2 **first boot automatically**:
  - ✅ Creates **2GB swap file** (`/swapfile`) — prevents t3.micro RAM crash
  - ✅ Persists swap via `/etc/fstab` — survives reboots
  - ✅ Installs Docker CE + Docker Compose plugin (official Docker apt repo)
  - ✅ Enables Docker at boot (`systemctl enable docker`)
  - ✅ Adds `ubuntu` user to `docker` group (no sudo needed)
  - ✅ Writes marker file at `/var/log/docker-bootstrap.done`

---

### 3. AWS Resources Provisioned (via `terraform apply`)
- [x] EC2 instance `t3.micro` — Ubuntu 24.04 LTS — 20GB gp3 disk
- [x] Security Group (`utility-billing-ai-prod-sg`):
  - Port **22** (SSH) — **admin IP only** (`76.37.28.153/32`) — not public
  - Port **80** (HTTP via Nginx) — open to world (`0.0.0.0/0`)
  - All outbound traffic allowed
- [x] IAM Role + Instance Profile — EC2 can read/write S3 bucket `utility-billing-storage`
- [x] Elastic IP attached to EC2

---

### 4. EC2 Server Specs (t3.micro)

| Resource | Value |
|----------|-------|
| vCPU | 2 (1 core, 2 threads) |
| RAM | 1 GB |
| **Swap** | **2 GB** (auto-created by bootstrap script) |
| Disk | 20 GB gp3 SSD |
| OS | Ubuntu 24.04 LTS |
| Docker | 29.3.0 |

**Why swap matters on t3.micro:**
```
Without swap:   RAM fills → EC2 kernel OOM → process killed / EC2 freezes
With 2GB swap:  RAM fills → overflow to disk → slower but stays alive
```

---

### 5. SSH & Key Management
- [x] EC2 key pair `utility-billing-key` created in AWS
- [x] PEM saved at `~/Desktop/utility-billing-key.pem`
- [x] Permissions: `chmod 400 ~/Desktop/utility-billing-key.pem`
- [x] SSH: `ssh -i ~/Desktop/utility-billing-key.pem ubuntu@<IP>`

---

### 6. Nginx Reverse Proxy Setup *(Security: hides Streamlit from public)*

- [x] `nginx/nginx.conf` created
- [x] `docker-compose.prod.yml` adds Nginx service on port 80

**Architecture:**
```
Browser → http://52.2.3.30 (port 80)
           ↓
        [Nginx container] — port 80 — only public entry point
           ↓ proxy_pass http://streamlit:8501
        [Streamlit container] — port 8501 — internal Docker network only
```

Same IP, same website: users should open the app at `http://52.2.3.30` only; Nginx is the public entry point and Streamlit stays private on the VM.

**The critical fix — why `127.0.0.1` was wrong:**
```nginx
# ❌ WRONG — 127.0.0.1 inside Nginx container = Nginx itself, NOT Streamlit
proxy_pass http://127.0.0.1:8501;

# ✅ CORRECT — Docker DNS resolves service name to Streamlit container's IP
proxy_pass http://streamlit:8501;
```
Each Docker container has its **own isolated network namespace**. Containers must
communicate via Docker service names (internal DNS), not `127.0.0.1`.

**`nginx/nginx.conf`:**
```nginx
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass         http://streamlit:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

**`docker-compose.prod.yml` (production overrides):**
```yaml
services:
  api:
    ports:
      - "127.0.0.1:8000:8000"   # API only reachable internally on EC2
  streamlit:
    ports: []                    # 8501 not public — Nginx handles it
  nginx:
    image: nginx:alpine
    ports:
      - "0.0.0.0:80:80"         # Only public entry point
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - streamlit
    restart: unless-stopped
```

---

### 7. Airflow Disabled for Production
- [x] Airflow placed behind Docker Compose `profiles: [airflow]`
- [x] Will **NOT start** unless explicitly run with `--profile airflow`
- [x] Prevents 500MB+ image from loading on t3.micro and crashing EC2

---

### 8. Repo & App Deployed on EC2
- [x] Repo cloned from `Dev` branch: `git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git`
- [x] `.env` copied to EC2 via `scp` (not in git — contains API keys/secrets)
- [x] All 3 containers built and started:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
  ```
- [x] DB initialized: `docker compose exec -T api python -m src.database.init_db`
- [x] API health check: `{"status":"ok"}` ✅
- [x] Nginx HTTP check: `HTTP Status: 200` ✅
- [x] App live at: **`http://52.2.3.30`** ✅

---

### 9. Running Container Status (verified 2026-03-18)
```
NAME                          IMAGE                          STATUS          PORTS
utility-api                   utility-billing-ai-api         Up (healthy)    127.0.0.1:8000->8000/tcp
utility-streamlit             utility-billing-ai-streamlit   Up              (internal only via Nginx)
utility-billing-ai-nginx-1    nginx:alpine                   Up              0.0.0.0:80->80/tcp
```

---

### 10. EC2 Auto Scheduler (Office Hours Start/Stop)
- [x] `terraform/scheduler.tf` created — all scheduler resources defined as Terraform code
- [x] Lambda `utility-billing-ai-prod-ec2-start` — Python 3.12, starts EC2 instance
- [x] Lambda `utility-billing-ai-prod-ec2-stop` — Python 3.12, stops EC2 instance
- [x] **Upgraded from CloudWatch Events → EventBridge Scheduler** (timezone-aware, DST auto-handled)
- [x] Schedule: `cron(0 9 ? * MON-FRI *)` **America/New_York** = **9:00 AM Mon–Fri (EST & EDT)**
- [x] Schedule: `cron(0 18 ? * MON-FRI *)` **America/New_York** = **6:00 PM Mon–Fri (EST & EDT)**
- [x] IAM roles: Lambda execution role + Scheduler invoke role (least-privilege)
- [x] `terraform apply` successful — all resources in AWS
- [x] **Current state: DISABLED** — manual start/stop mode active

**Why EventBridge Scheduler instead of CloudWatch Events:**
```
CloudWatch Events → UTC crons only → manual UTC math each time clocks change
EventBridge Scheduler → America/New_York timezone → DST handled automatically forever
```

**Cost saving:** ~$2–3/month (office hours) vs ~$8/month (24/7 running)

---

### 11. Manual Start / Stop (Current Active Mode)

- [x] EC2 started/stopped manually via AWS CLI — no scheduler dependency
- [x] Elastic IP retained on stop — same IP `52.2.3.30` every time
- [x] Docker containers auto-restart on EC2 boot (`restart: unless-stopped`)

**Daily commands:**
```bash
# Start EC2 (app live in ~60 sec at http://52.2.3.30)
aws ec2 start-instances --region us-east-1 --instance-ids i-06ebc19f707862bdd

# Stop EC2 (IP + data preserved)
aws ec2 stop-instances --region us-east-1 --instance-ids i-06ebc19f707862bdd
```

**Enable/Disable scheduler:**
```bash
# Enable auto-scheduler
aws scheduler update-schedule --region us-east-1 --name utility-billing-ai-prod-ec2-start \
  --state ENABLED --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-start,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

aws scheduler update-schedule --region us-east-1 --name utility-billing-ai-prod-ec2-stop \
  --state ENABLED --schedule-expression "cron(0 18 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-stop,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

# Disable auto-scheduler (back to manual)
aws scheduler update-schedule --region us-east-1 --name utility-billing-ai-prod-ec2-start \
  --state DISABLED --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-start,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role

aws scheduler update-schedule --region us-east-1 --name utility-billing-ai-prod-ec2-stop \
  --state DISABLED --schedule-expression "cron(0 18 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" --flexible-time-window Mode=OFF \
  --target Arn=arn:aws:lambda:us-east-1:150758096185:function:utility-billing-ai-prod-ec2-stop,RoleArn=arn:aws:iam::150758096185:role/utility-billing-ai-prod-scheduler-invoke-role
```

---

## ⏳ REMAINING / PENDING

### Phase 2 — HTTPS / SSL / Domain *(Next step after current deploy is stable)*

Right now the app runs on plain HTTP (`http://52.2.3.30`). To make it production-secure:

| Option | What it needs | Cost |
|--------|---------------|------|
| **A — Self-signed cert** | Just Nginx config | Free but browser shows "Not Secure" warning |
| **B — Let's Encrypt (Certbot)** | A domain name pointed at EC2 IP | Domain ~$10/yr, SSL cert Free |
| **C — AWS Certificate Manager** | AWS ALB + Route 53 domain | More complex, managed by AWS |

**Recommended path:**
1. Get a domain (or use a free subdomain)
2. Point DNS `A record` → `52.2.3.30`
3. Run Certbot on EC2 → auto-issues free SSL cert
4. Update Nginx to listen on 443, redirect HTTP → HTTPS

---

### Phase 3 — Operations / Monitoring *(Optional, future)*
- [ ] Set up CloudWatch or UptimeRobot alerts
- [ ] Automated DB backup to S3
- [ ] Enable Airflow when pipeline scheduling is needed (`--profile airflow`)
- [ ] Set up log rotation for Docker container logs

---

## 📋 HOW TO REPRODUCE ON ANY NEW SERVER (Full Runbook)

This setup is **fully automated via Terraform**. To spin up an identical server from scratch:

```bash
# ── STEP 1: Clone repo locally ──────────────────────────────────────────────
git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git
cd utility-billing-ai/terraform

# ── STEP 2: Configure your values ───────────────────────────────────────────
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars:
#   admin_ip  = "YOUR.PUBLIC.IP.HERE/32"   # from https://checkip.amazonaws.com
#   key_name  = "utility-billing-key"       # must exist in AWS

# ── STEP 3: Provision AWS infrastructure ────────────────────────────────────
# This automatically creates: EC2 + Security Group + IAM + EIP
# AND runs bootstrap on first boot: 2GB swap + Docker installed
terraform init
terraform apply

# ── STEP 4: Get new IP and copy .env ────────────────────────────────────────
NEW_IP=$(terraform output -raw instance_public_ip)
scp -i ~/Desktop/utility-billing-key.pem .env ubuntu@$NEW_IP:~/.env

# ── STEP 5: SSH in and deploy ────────────────────────────────────────────────
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@$NEW_IP

# Inside EC2:
git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git ~/utility-billing-ai
cp ~/.env ~/utility-billing-ai/.env
cd ~/utility-billing-ai
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db

# ── STEP 6: Verify ───────────────────────────────────────────────────────────
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/api/v1/health/live
curl -I http://127.0.0.1:80
# Open browser: http://<NEW_IP>
```

> **Note:** `.env` must always be copied manually — it has secrets and is NOT in git.

---

## 🔑 Quick Reference Commands

```bash
# SSH into EC2
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@52.2.3.30

# Check memory + swap
free -h && swapon --show

# Check container status
cd ~/utility-billing-ai
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Start all services (prod — api + streamlit + nginx)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api streamlit nginx

# Start with Airflow (when needed)
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile airflow up -d

# View logs
docker compose logs -f api
docker compose logs -f streamlit
docker compose logs -f nginx

# API health check (from inside EC2)
curl http://127.0.0.1:8000/api/v1/health/live

# Stop all containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Terraform — rebuild everything from scratch (WARNING: new IP assigned)
cd ~/utility-billing-ai/terraform
terraform destroy    # ⚠️ IP will change
terraform apply

# Terraform — safe to reapply without destroying
terraform apply      # only changes what's different
```
