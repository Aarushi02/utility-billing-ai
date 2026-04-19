# Deployment Runbook (API + Streamlit + Nginx)

This runbook covers three services for production deployment:

1. FastAPI backend (`api`) — internal only, not public
2. Streamlit frontend (`streamlit`) — served via Nginx and bound to localhost on the VM, not directly public
3. Nginx reverse proxy (`nginx`) — the only public entry point on port 80

Airflow is intentionally out of scope in this guide (disabled by default via Docker Compose profiles).

---

## 1) Prerequisites

- Docker Engine + Compose plugin (auto-installed on EC2 via bootstrap script)
- `.env` is **auto-generated** by `scripts/fetch_secrets.sh` from AWS SSM Parameter Store — no manual copy needed
- AWS credentials: `~/.aws/credentials` with Troy & Banks account (`335971291943`, region `us-east-2`)
- Ports needed:
  - `80` for Nginx (public — only port open in Security Group)
  - `8000` for API (internal only — bound to `127.0.0.1`)
     - `8501` for Streamlit (internal only — bound to `127.0.0.1` on the VM and accessed via Nginx)

---

## 2) Local Docker Test (Development)

### Start API + Streamlit only (no Nginx needed locally)

```bash
docker compose up -d --build api streamlit
```

### Check container health

```bash
docker compose ps
```

Expected:
- `utility-api` is `Up ... (healthy)`
- `utility-streamlit` is `Up`

### Verify endpoints

```bash
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
```

Expected:
- API returns `{"status":"ok"}`
- Streamlit returns HTTP `200`

### Open UI (local)

- http://127.0.0.1:8501

### Stop services

```bash
docker compose down
```

---

## 3) Production Topology

Traffic flow with Nginx:

```
Browser → http://3.12.193.9 (port 80)
              ↓
         [Nginx container]   — only public entry point
              ↓ proxy_pass http://streamlit:8501
         [Streamlit container]  — internal Docker network
              ↓ http://api:8000
         [API container]        — internal only
```

**Why this matters:**
- Port `8501` is NOT exposed publicly in production
- Port `8000` is NOT exposed publicly
- Only port `80` (Nginx) is open in the AWS Security Group
- Docker containers communicate via service names (`streamlit`, `api`) — NOT `127.0.0.1`

---

## 4) Production Deploy Command

Always use both compose files for production:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
```

The `docker-compose.prod.yml` overrides:
- API: bound to `127.0.0.1:8000` only
- Streamlit: `ports: []` in production; the base compose also binds Streamlit to `127.0.0.1:8501` so it stays local to the VM if someone starts the app without prod overrides
- Nginx: added as a service on `0.0.0.0:80`

---

## 5) Environment Variables — How They Are Managed

**Do NOT manually create or copy `.env` files.** All secrets are in AWS SSM Parameter Store.

### On EC2 (production)
`.env` is written automatically by the systemd boot service. You can also refresh manually:
```bash
cd ~/utility-billing-ai
./scripts/fetch_secrets.sh
```

### Locally (development)
```bash
aws configure          # use Troy & Banks IAM credentials, region us-east-2
./scripts/fetch_secrets.sh    # writes .env from SSM
```

### Key variables managed in SSM
- `DB_TYPE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — DB_URL is built at runtime by `config.py`, not stored
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `AWS_BUCKET_NAME`, `AWS_REGION` — EC2 uses IAM role for S3; no static keys in `.env`
- `LOGIC_USERNAME`, `LOGIC_PASSWORD`

### To update a secret
1. Edit `terraform/terraform.tfvars` (gitignored)
2. Run `cd terraform && terraform apply`
3. On EC2: `./scripts/fetch_secrets.sh && docker compose ... restart`

---

## 6) Initialize Database

Run once after first deploy (or after `docker compose down`):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db
```

---

## 7) Verify Production Health

From inside EC2:

```bash
# API internal health
curl -sS http://127.0.0.1:8000/api/v1/health/live

# Nginx → Streamlit public check
curl -sS -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:80
```

From browser:
- `http://3.12.193.9` → should load Streamlit app (via Nginx)
- `http://3.12.193.9:8501` → should NOT be reachable (port blocked by Security Group)
- `http://3.12.193.9:8000` → should NOT be reachable

Same IP, same website: users keep using the Elastic IP, but the website is meant to be opened only at `http://3.12.193.9` on port `80`.

---

## 8) Troubleshooting

### API keeps restarting

```bash
docker compose logs --tail=200 api
```

### Streamlit can't fetch backend

1. Confirm API health endpoint responds
2. Confirm `API_BASE_URL=http://api:8000` in `.env`
3. Restart services:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
```

### Nginx 502 Bad Gateway

Nginx can't reach Streamlit. Check:

```bash
docker compose logs --tail=50 nginx
docker compose ps   # confirm streamlit is Up and healthy
```

The `nginx.conf` must use `proxy_pass http://streamlit:8501` — NOT `127.0.0.1:8501`.

### Clean restart

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m src.database.init_db
```

### EC2 freezing / out of memory

Check swap:

```bash
free -h && swapon --show
```

Expected: `Swap: 2.0Gi` — if missing, EC2 was recreated without bootstrap. The bootstrap script auto-creates swap on first boot. Verify:

```bash
sudo cat /var/log/docker-bootstrap.done
```

---

## 9) Related Docs

- `documentation/DEPLOYMENT.md` — local + AWS deployment guide
- `documentation/AWS_REUSE_SETUP_RUNBOOK.md` — full cloud setup from scratch
- `documentation/SECRETS_MANAGEMENT.md` — SSM Parameter Store secrets workflow
- `documentation/DISASTER_RECOVERY_RUNBOOK.md` — EC2/EIP recovery steps
- `documentation/DEPLOYMENT_PROGRESS_CHECKLIST.md` — current status and pending steps
- `nginx/nginx.conf` — Nginx reverse proxy configuration
- `docker-compose.prod.yml` — production port binding overrides
