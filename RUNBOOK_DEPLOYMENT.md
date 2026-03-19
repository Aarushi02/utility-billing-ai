# Deployment Runbook (API + Streamlit + Nginx)

This runbook covers three services for production deployment:

1. FastAPI backend (`api`) — internal only, not public
2. Streamlit frontend (`streamlit`) — served via Nginx, not directly public
3. Nginx reverse proxy (`nginx`) — the only public entry point on port 80

Airflow is intentionally out of scope in this guide (disabled by default via Docker Compose profiles).

---

## 1) Prerequisites

- Docker Engine + Compose plugin (auto-installed on EC2 via bootstrap script)
- A valid `.env` file in project root
- Ports needed:
  - `80` for Nginx (public — only port open in Security Group)
  - `8000` for API (internal only — bound to `127.0.0.1`)
  - `8501` for Streamlit (internal only — accessed via Nginx)

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
Browser → http://52.2.3.30 (port 80)
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
- Streamlit: `ports: []` — no direct public port
- Nginx: added as a service on `0.0.0.0:80`

---

## 5) Environment Variables You Must Set

Minimum required:

- `LOGIC_USERNAME`
- `LOGIC_PASSWORD`
- `DB_TYPE` (`postgres` recommended in production)
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `API_BASE_URL=http://api:8000`

Optional but common:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AWS_BUCKET_NAME`
- `AWS_REGION`
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (not needed if using EC2 IAM role)

Notes:

- Keep `.env` only on the server — never commit secrets to git
- On EC2 with IAM instance profile, static AWS keys can be omitted

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
- `http://52.2.3.30` → should load Streamlit app (via Nginx)
- `http://52.2.3.30:8501` → should NOT be reachable (port blocked by Security Group)
- `http://52.2.3.30:8000` → should NOT be reachable

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
- `documentation/DEPLOYMENT_PROGRESS_CHECKLIST.md` — current status and pending steps
- `nginx/nginx.conf` — Nginx reverse proxy configuration
- `docker-compose.prod.yml` — production port binding overrides
