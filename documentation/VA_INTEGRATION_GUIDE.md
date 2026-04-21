# VA Integration Guide — NY Internal Reference

Complete record of what was built, every file changed, and how to maintain it.

---

## Architecture

```
Single EC2  (i-0393dd4f827866db2, us-east-2)
Single IP   (3.12.193.9)
Single nginx on port 80

http://3.12.193.9/     → Portal page → NY Audit  (utility-streamlit:8501)
http://3.12.193.9/va   → VA Audit               (utility-va-streamlit:8501 internal / 8502 host)
```

**VA Repo:** `https://github.com/vinayjain38/TroyBanks_Audit_Demo_VA`
**VA on EC2:** `/home/ubuntu/va-billing-ai` (cloned once manually)

---

## How Deployment Works

### Triggers
1. Push to `main` → immediate deploy
2. `workflow_dispatch` → manual trigger from GitHub Actions UI
3. **Schedule: 9:15 AM EST Mon–Fri** → auto deploy pulls latest from both repos

### What the Deploy Script Does (line 38 of deploy.yml)
```bash
# NY
cd /home/ubuntu/utility-billing-ai
git fetch origin main && git reset --hard origin/main
bash scripts/fetch_secrets.sh              # writes .env from SSM /utility-billing-ai/prod/
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# VA (only if folder exists on EC2)
if [ -d /home/ubuntu/va-billing-ai ]; then
  cd /home/ubuntu/va-billing-ai
  git fetch origin main && git reset --hard origin/main
  bash /home/ubuntu/utility-billing-ai/scripts/fetch_secrets.sh prod .env
  docker compose -f docker-compose.prod.yml up -d --build backend frontend
fi

docker compose -f /home/ubuntu/utility-billing-ai/docker-compose.yml ps
```

### VA Git Remote
The VA repo URL is not in deploy.yml — it's stored in EC2 git config from the one-time clone:
```
/home/ubuntu/va-billing-ai/.git/config  →  url = https://github.com/vinayjain38/TroyBanks_Audit_Demo_VA.git
```

---

## Every File Changed For This Integration

### 1. `app/components/portal.py` — NEW FILE
Service selection portal shown after login. Two cards: NY Audit and VA Audit.
- NY button: sets `session_state.selected_service = "ny"` → stays in app
- VA button: `st.link_button` → opens VA at `/va` in new tab
- Logout button top-right (same style as main app)
- `VA_STREAMLIT_URL` env var controls the VA redirect URL (default `/va`)

### 2. `app/streamlit_app.py` — MODIFIED
- Import `render_portal` added
- After login check: if `selected_service` not in session → show portal, stop
- Top bar updated: added `🏠 Home` button (col2) that clears `selected_service` and returns to portal
- Column layout changed from `[2.8, 0.5, 0.3]` to `[2.2, 0.7, 0.5, 0.3]` to fit Home button

### 3. `nginx/nginx.conf` — MODIFIED
Two key changes:
- Added `resolver 127.0.0.11 valid=10s ipv6=off` — Docker DNS resolver prevents nginx from caching upstream IPs (fixes 502 after container restarts)
- Added `/va` location block routing to `utility-va-streamlit:8501`
- Uses `set $upstream` variable pattern (required when using resolver)

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;

location /va {
    set $va_upstream http://utility-va-streamlit:8501;
    proxy_pass $va_upstream;
    # + websocket headers, timeout
}
location / {
    set $ny_upstream http://streamlit:8501;
    proxy_pass $ny_upstream;
}
```

### 4. `docker-compose.yml` — MODIFIED
- Added `va-api` and `va-streamlit` services with `profiles: [va]`
- `profiles: [va]` means NY CI/CD (`docker compose up`) never touches these containers
- Added `VA_STREAMLIT_URL: /va` env var to NY streamlit service
- VA containers reference same Dockerfiles as NY (placeholder — VA team uses their own)

### 5. `docker-compose.prod.yml` — MODIFIED
- Added `va-api` and `va-streamlit` port overrides
- nginx `depends_on` only includes `streamlit` (not `va-streamlit`) — VA containers are profiled so they'd cause "undefined service" error otherwise
- nginx `restart: unless-stopped` confirmed

### 6. `scripts/fetch_secrets.sh` — MODIFIED
Added support for project name as 3rd argument:
```bash
# Before: PROJECT hardcoded as "utility-billing-ai"
# After:
PROJECT="${3:-${SSM_PROJECT:-utility-billing-ai}}"

# Usage for VA:
bash scripts/fetch_secrets.sh prod .env va-billing-ai
# fetches from /va-billing-ai/prod/ in SSM
```

### 7. `.github/workflows/deploy.yml` — MODIFIED
Three changes:
1. Added VA deploy block inside `if [ -d /home/ubuntu/va-billing-ai ]` guard
2. VA uses `docker compose -f docker-compose.prod.yml up -d --build backend frontend` (their prod file, only 2 services — skips Airflow)
3. Added scheduled trigger: `cron: '15 13 * * 1-5'` (9:15 AM EST Mon–Fri)

---

## Port Reference

| Service | Container Name | Host Port | Internal Port |
|---|---|---|---|
| NY API | `utility-api` | `127.0.0.1:8000` | `8000` |
| NY Streamlit | `utility-streamlit` | `127.0.0.1:8501` | `8501` |
| VA API | `utility-va-api` | `8001` | `8000` |
| VA Streamlit | `utility-va-streamlit` | `8502` | `8501` |
| nginx | `utility-billing-ai-nginx-1` | `0.0.0.0:80` | `80` |

Docker network shared by all: `utility-billing-ai_default`

---

## SSM Secrets

| Team | SSM Path | Written To |
|---|---|---|
| NY | `/utility-billing-ai/prod/*` | `/home/ubuntu/utility-billing-ai/.env` |
| VA | same `/utility-billing-ai/prod/*` | `/home/ubuntu/va-billing-ai/.env` |

VA currently shares NY's secrets. If VA needs separate secrets in future:
- Add to SSM under `/va-billing-ai/prod/`
- Change deploy.yml VA fetch line to: `bash scripts/fetch_secrets.sh prod .env va-billing-ai`

---

## One-Time EC2 Setup (Already Done)

```bash
# Clone VA repo — done once, never needs repeating
aws ssm send-command \
  --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" \
  --region "us-east-2" \
  --parameters commands='["cd /home/ubuntu && git clone https://github.com/vinayjain38/TroyBanks_Audit_Demo_VA.git va-billing-ai"]'
```

---

## What VA Team Must Have In Their docker-compose.prod.yml

```yaml
services:
  backend:
    container_name: utility-va-api
    ports:
      - "8001:8000"

  frontend:
    container_name: utility-va-streamlit
    ports:
      - "8502:8501"
    environment:
      STREAMLIT_SERVER_BASE_URL_PATH: /va

networks:
  default:
    name: utility-billing-ai_default
    external: true
```

---

## Troubleshooting

**502 on `/va` after deploy**
nginx DNS cache — restart nginx:
```bash
aws ssm send-command --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" --region "us-east-2" \
  --parameters commands='["docker restart utility-billing-ai-nginx-1"]'
```

**VA containers not starting**
Check logs:
```bash
aws ssm send-command --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" --region "us-east-2" \
  --parameters commands='["docker logs utility-va-streamlit --tail 50"]'
```

**Check all containers**
```bash
aws ssm send-command --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" --region "us-east-2" \
  --parameters commands='["docker ps"]'
```

**VA code not updating**
Verify VA repo has latest on main branch and wait for 9:15 AM EST deploy, or trigger manually via GitHub Actions → workflow_dispatch.
