# VA Team — Integration Handoff Document

Everything you need to know about how your service is deployed and runs on our shared infrastructure.

---

## What We Built Together

Both NY Audit and VA Audit run on the **same AWS EC2 server** under the **same public IP**.
Users access a shared portal page and choose which service to open.

```
http://3.12.193.9/      → Shared portal (NY login + service selection)
http://3.12.193.9/va    → Your Virginia Audit app
http://3.12.193.9/      → New York Audit app (after selecting NY)
```

---

## How Your App Is Deployed

### Your Repo
```
https://github.com/vinayjain38/TroyBanks_Audit_Demo_VA
```
This is cloned on our EC2 at `/home/ubuntu/va-billing-ai`.

### Automatic Daily Deploy — 9:15 AM EST (Mon–Fri)
Every weekday morning our GitHub Actions pipeline runs automatically and:
1. Pulls **latest code** from your `main` branch
2. Fetches secrets from AWS SSM
3. Runs `docker compose -f docker-compose.prod.yml up -d --build backend frontend`

**So: push to your `main` branch → live next morning. No manual steps needed.**

### Also Triggers On
- Every time NY team pushes to their `main` branch
- Manual trigger via GitHub Actions `workflow_dispatch`

---

## Your docker-compose.prod.yml (Required Config)

Your `docker-compose.prod.yml` must have these exact values for our nginx to route traffic correctly:

```yaml
services:
  backend:
    container_name: utility-va-api        # exact — nginx uses this name
    ports:
      - "8001:8000"                        # must be 8001, not 8000

  frontend:
    container_name: utility-va-streamlit  # exact — nginx uses this name
    ports:
      - "8502:8501"                        # must be 8502
    environment:
      STREAMLIT_SERVER_BASE_URL_PATH: /va  # required for /va routing

networks:
  default:
    name: utility-billing-ai_default      # must join our shared network
    external: true
```

**Do not change container names or ports** — nginx is hardcoded to route to these.

---

## Environment Variables

Your `.env` is generated automatically from **AWS SSM Parameter Store** before each deploy.

We currently share the same SSM secrets as NY (`/utility-billing-ai/prod/`).
If you need VA-specific secrets in future, let NY team know and they will add them to SSM under `/va-billing-ai/prod/`.

---

## Port Reference

| Service | Container Name | Port |
|---|---|---|
| Your API | `utility-va-api` | `8001` (internal) |
| Your Streamlit | `utility-va-streamlit` | `8502` (internal) |
| NY API | `utility-api` | `8000` (internal) |
| NY Streamlit | `utility-streamlit` | `8501` (internal) |
| nginx (public) | `utility-billing-ai-nginx-1` | `80` |

All containers are on Docker network: `utility-billing-ai_default`

---

## How nginx Routes Traffic

```
User visits 3.12.193.9/va
      ↓
nginx sees /va prefix
      ↓
Forwards request to utility-va-streamlit:8501 (internal)
      ↓
Your Streamlit app responds
```

Your Streamlit must always run with `--server.baseUrlPath=/va` (already set via `STREAMLIT_SERVER_BASE_URL_PATH`).

---

## What Happens If You Push New Code

```
You push to your main branch
      ↓
Wait until next morning 9:15 AM EST
      ↓
Our deploy pipeline pulls your latest code automatically
      ↓
Rebuilds your containers
      ↓
Your new code is live at http://3.12.193.9/va
```

---

## What You Must NOT Change

| Thing | Why |
|---|---|
| `container_name: utility-va-api` | nginx routes by this exact name |
| `container_name: utility-va-streamlit` | nginx routes by this exact name |
| Port `8001` for backend | hardcoded in our infrastructure |
| Port `8502` for frontend | hardcoded in our infrastructure |
| `networks: utility-billing-ai_default` | must be on our Docker network |
| `--server.baseUrlPath=/va` | required for all asset URLs to work under /va |

---

## If Something Goes Wrong

Contact NY team. They can:
- Check container status on EC2
- Restart containers
- Trigger a manual redeploy
- Check logs


