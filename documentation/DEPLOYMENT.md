# Utility Billing AI — Deployment Guide

This project uses `docker-compose.yml` as the base config and `docker-compose.prod.yml` as the production override. Together they handle local testing and cloud (AWS EC2) production deployment.

---

## A) Local Smoke Test (Development)

Start API + Streamlit only (Nginx not needed locally):

```bash
docker compose up -d --build api streamlit
```

Verify:

```bash
docker compose ps
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
```

Expected:

1. API health returns `{"status":"ok"}`
2. Streamlit returns `200`

Open UI: http://127.0.0.1:8501

Stop:

```bash
docker compose down
```

---

## B) EC2 Production (Single-VM with Nginx)

### Architecture

```
Browser → http://<EC2_IP> (port 80)
              ↓
         Nginx container     — only public port (80)
              ↓ proxy_pass http://streamlit:8501
      Streamlit container — internal Docker network only, bound to localhost on the VM
              ↓ http://api:8000
         API container       — internal only
```

Same IP, same website: the app should be opened only at the Elastic IP on port 80, for example `http://3.12.193.9`.

**Key security points:**
- Streamlit is **NOT** directly public — Nginx proxies all traffic
- API is **NOT** publicly reachable — internal only
- Airflow is **disabled** by default (Docker Compose profile)
- Only port `80` is open in the AWS Security Group

### 1) AWS Infrastructure Setup

Use Terraform (fully automated):

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform provisions:
- EC2 `t3.micro` — Ubuntu 24.04 — 20GB gp3 disk
- Security Group: port 22 (your IP only) + port 80 (public)
- IAM Role + Instance Profile (S3 access)
- Elastic IP
- Bootstrap script on first boot: **2GB swap + Docker CE installed automatically**

### 2) Copy .env to EC2

```bash
# Get IP from terraform output
EC2_IP=$(cd terraform && terraform output -raw instance_public_ip)

# Copy .env (never commit secrets to git)
scp -i ~/Desktop/utility-billing-key.pem .env ubuntu@$EC2_IP:~/.env
```

### 3) SSH and Deploy

```bash
ssh -i ~/Desktop/utility-billing-key.pem ubuntu@$EC2_IP

# Inside EC2:
git clone -b Dev https://github.com/harshalsp0011/utility-billing-ai.git ~/utility-billing-ai
cp ~/.env ~/utility-billing-ai/.env
cd ~/utility-billing-ai

# Start API + Streamlit + Nginx (production mode)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx

# Initialize database
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db
```

### 4) Verify Production

From EC2:

```bash
# API internal health
curl -sS http://127.0.0.1:8000/api/v1/health/live

# Nginx → Streamlit (public entry point)
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:80
```

Expected:

1. API health returns `{"status":"ok"}`
2. Nginx returns `200`

From browser:

1. `http://<EC2_PUBLIC_IP>` — works (Nginx on port 80)
2. `http://<EC2_PUBLIC_IP>:8501` — should NOT be reachable (blocked by Security Group)
3. `http://<EC2_PUBLIC_IP>:8000` — should NOT be reachable

If you redeploy and still see port 8501 published locally in `docker compose ps`, recreate the containers from the updated repo. The hardened state is `http://<EC2_PUBLIC_IP>` only.

---

## C) Nginx Configuration

**File:** `nginx/nginx.conf`

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

**Important:** `proxy_pass` uses `http://streamlit:8501` — the Docker service name. Using `127.0.0.1` would point to the Nginx container itself, not Streamlit.

**File:** `docker-compose.prod.yml`

```yaml
services:
  api:
    ports:
      - "127.0.0.1:8000:8000"  # API only reachable on EC2 itself
  streamlit:
    ports: []                   # No direct public port — Nginx handles it
  nginx:
    image: nginx:alpine
    ports:
      - "0.0.0.0:80:80"        # Only public entry point
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - streamlit
    restart: unless-stopped
```

---

## D) Required Environment Variables

Minimum:

1. `DB_TYPE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
2. `LOGIC_USERNAME`, `LOGIC_PASSWORD`
3. `API_BASE_URL=http://api:8000`

Recommended:

1. `OPENAI_API_KEY`, `OPENAI_MODEL`
2. `AWS_BUCKET_NAME`, `AWS_REGION`
3. Prefer IAM role over static AWS access keys on EC2

---

## E) Operate / Troubleshoot

Check status:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Restart services:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
```

View logs:

```bash
docker compose logs --tail=200 api
docker compose logs --tail=200 streamlit
docker compose logs --tail=200 nginx
```

Clean restart:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db
```

Enable Airflow (when needed):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile airflow up -d
```

---

## F) Simple Security Plan (Non-Technical)

Use this order:

1. Step 1 now: tighten Security Group.
  - Keep website port `80` open.
  - Keep admin port `22` limited to one trusted IP.
  - Keep `8000`, `8501`, and `8080` closed publicly.

2. Step 2 next: add HTTPS.
  - Move site from `http://` to `https://`.
  - Redirect HTTP to HTTPS.

3. Step 3 later: move to ALB + private EC2 + NAT.
  - Public traffic hits ALB.
  - App server has no public IP.

Why this order:
1. Step 1 gives quick protection with almost no cost impact.
2. Step 2 protects user data in transit.
3. Step 3 is the strongest pattern but adds recurring AWS cost.
