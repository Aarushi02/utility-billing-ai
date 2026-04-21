# VA Integration Guide

Full record of what has been done, what VA team must do, and what NY team still needs to complete.

---

## Architecture

Both NY and VA run on the same EC2 instance. Single IP, single nginx, two apps.

```
http://3.12.193.9/     → New York Audit  (NY streamlit  → NY API)
http://3.12.193.9/va   → Virginia Audit  (VA streamlit  → VA API)
```

**VA Repo:** `https://github.com/vinayjain38/TroyBanks_Audit_Demo_VA`

---

## What Has Been Done (NY Side)

### Infrastructure & Routing
- [x] nginx updated — `/va` routes to `utility-va-streamlit:8501`, `/` stays NY
- [x] Docker DNS resolver (`127.0.0.11`) added to nginx so it finds VA containers dynamically after restarts
- [x] `va-api` and `va-streamlit` added to `docker-compose.yml` with `profiles: [va]` so NY CI/CD never builds or touches them
- [x] `docker-compose.va-override.yml` created — maps VA's `backend`/`frontend` services to our required container names, ports, network, and `/va` base path without touching their code

### Portal Page
- [x] Service selection portal added after login — user chooses NY Audit or VA Audit
- [x] NY Audit stays in current app, VA Audit redirects to `/va`
- [x] Logout button on portal page
- [x] 🏠 Home button on every NY page — returns to portal from anywhere

### Deploy Pipeline
- [x] `fetch_secrets.sh` updated — now accepts project name as argument so it can fetch from `/va-billing-ai/prod/` in SSM (same pattern as NY uses `/utility-billing-ai/prod/`)
- [x] `deploy.yml` updated — after NY deploy, pulls VA repo and deploys `backend` + `frontend` only (skips their Airflow stack)
- [x] VA repo cloned on EC2 at `/home/ubuntu/va-billing-ai` (one-time, already done)
- [x] VA deploy injects `API_HOST_PORT=8001` and `STREAMLIT_HOST_PORT=8502` into VA's `.env`

### Current Deploy Flow
```
Push to NY main
      ↓
GitHub Actions
      ↓
SSM → EC2:
  1. Pull NY code → fetch NY secrets from SSM → docker compose up (NY only)
  2. Pull VA code → fetch VA secrets from SSM → docker compose up (backend + frontend only)
      ↓
Both apps live, nginx routes traffic
```

---

## What VA Team Must Provide

### 1. Their `.env` Variable Names + Values
Share securely (not over email). You will load each one into AWS SSM.

Ask them for a list like:
```
DATABASE_URL=...
OPENAI_API_KEY=...
SECRET_KEY=...
... etc
```

### 2. Confirm Their docker-compose Uses These Ports (Already Wired)
VA's repo already uses `${API_HOST_PORT}` and `${STREAMLIT_HOST_PORT}` env vars — our deploy injects the correct values automatically. No changes needed on their side.

---

## What NY Team Still Needs To Do

### Step 1 — Load VA Secrets Into SSM
Once VA team shares their `.env`, run this for each variable:

```bash
aws ssm put-parameter \
  --name "/va-billing-ai/prod/VARIABLE_NAME" \
  --value "their-value" \
  --type SecureString \
  --region us-east-2
```

Example:
```bash
aws ssm put-parameter --name "/va-billing-ai/prod/DATABASE_URL" --value "postgresql://..." --type SecureString --region us-east-2
aws ssm put-parameter --name "/va-billing-ai/prod/OPENAI_API_KEY" --value "sk-..." --type SecureString --region us-east-2
```

Repeat for every variable in their `.env`.

### Step 2 — Grant EC2 IAM Role Access to VA SSM Path
The EC2 IAM role currently has access to `/utility-billing-ai/prod/*` only.
You need to add `/va-billing-ai/prod/*` to the policy.

In `terraform/secrets.tf` (or via AWS Console → IAM), add:
```
arn:aws:ssm:us-east-2:*:parameter/va-billing-ai/prod/*
```
to the existing SSM read policy on the EC2 role.

### Step 3 — Re-enable VA Health Check
Currently the VA health check is disabled in `docker-compose.va-override.yml` because VA containers had no env vars and were crashing.

Once VA secrets are loaded into SSM, remove the `healthcheck: disable: true` block from [docker-compose.va-override.yml](../docker-compose.va-override.yml):

```yaml
# Remove these 2 lines from backend section:
healthcheck:
  disable: true
```

Commit, PR, merge — deploy will test the health check with real secrets.

### Step 4 — Test End to End
| URL | Expected |
|---|---|
| `http://3.12.193.9/` | Portal page (NY + VA cards) |
| Portal → New York Audit | NY dashboard loads |
| Portal → Virginia Audit | VA Streamlit loads at `/va` |
| Portal → Logout | Returns to login |

---

## Port Reference

| Service | Container Name | Internal Port |
|---|---|---|
| NY API | `utility-api` | 8000 |
| NY Streamlit | `utility-streamlit` | 8501 |
| VA API | `utility-va-api` | 8001 |
| VA Streamlit | `utility-va-streamlit` | 8502 |
| nginx | `utility-billing-ai-nginx-1` | 80 (public) |

---

## SSM Secret Paths

| Team | SSM Path | Fetched To |
|---|---|---|
| NY | `/utility-billing-ai/prod/*` | `/home/ubuntu/utility-billing-ai/.env` |
| VA | `/va-billing-ai/prod/*` | `/home/ubuntu/va-billing-ai/.env` |

---

## Key Files Changed (NY Repo)

| File | What Changed |
|---|---|
| `app/components/portal.py` | New — service selection portal after login |
| `app/streamlit_app.py` | Portal shown after login, Home button added |
| `nginx/nginx.conf` | `/va` routing + Docker DNS resolver |
| `docker-compose.yml` | VA containers added with `profiles: [va]` |
| `docker-compose.va-override.yml` | New — maps VA services to our ports/names/network |
| `docker-compose.prod.yml` | VA port overrides, nginx depends_on cleaned |
| `scripts/fetch_secrets.sh` | Accepts project name arg for VA SSM path |
| `.github/workflows/deploy.yml` | Deploys VA repo after NY on every push to main |
| `documentation/VA_INTEGRATION_GUIDE.md` | This file |

---

## Troubleshooting

**502 on `/va`**
VA containers not running or not on correct network.
```bash
docker ps | grep va
docker network inspect utility-billing-ai_default | grep va
```

**VA deploy fails with "no parameters found"**
VA secrets not loaded into SSM yet — complete Step 1 above.

**VA deploy fails with "unhealthy"**
VA secrets loaded but health check still disabled — complete Step 3 above.

**502 on `/` after deploy**
nginx DNS cache stale — restart nginx:
```bash
aws ssm send-command --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" --region "us-east-2" \
  --parameters commands='["docker restart utility-billing-ai-nginx-1"]'
```
