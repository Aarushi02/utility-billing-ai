# VA Integration Guide

How to onboard the Virginia Audit service onto the shared EC2 alongside New York Audit.

---

## Overview

Both NY and VA run on the same EC2 instance (`i-0393dd4f827866db2`, `us-east-2`).
Nginx routes traffic based on path:

```
http://3.12.193.9/     → New York Audit (port 8501)
http://3.12.193.9/va   → Virginia Audit (port 8502)
```

---

## What To Send VA Team

Send them this message:

> Since your repo is public, we just need two things:
>
> **1. Your GitHub repo URL**
> e.g. `https://github.com/va-org/va-billing-ai`
>
> **2. Your `docker-compose.yml` must use these exact values:**
>
> ```yaml
> services:
>   va-api:
>     container_name: utility-va-api
>     ports:
>       - "127.0.0.1:8001:8000"
>     restart: unless-stopped
>
>   va-streamlit:
>     container_name: utility-va-streamlit
>     ports:
>       - "127.0.0.1:8502:8501"
>     command: ["streamlit", "run", "your_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.baseUrlPath=/va"]
>     restart: unless-stopped
>
> networks:
>   default:
>     name: utility-billing-ai_default
>     external: true
> ```
>
> The `networks` section is mandatory — without it VA containers won't be reachable by nginx.
> Container names must match exactly.
> Once you share the URL we handle everything on our end.

---

## After VA Team Shares Their Repo URL

### Step 1 — Clone VA Repo on EC2 (One Time Only)

Run this from your local machine:

```bash
aws ssm send-command \
  --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" \
  --region "us-east-2" \
  --parameters commands='["cd /home/ubuntu && git clone https://github.com/<va-org>/va-billing-ai.git"]' \
  --query "Command.CommandId" \
  --output text
```

Replace `<va-org>/va-billing-ai` with their actual repo URL.

Verify it cloned:
```bash
aws ssm send-command \
  --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" \
  --region "us-east-2" \
  --parameters commands='["ls /home/ubuntu/va-billing-ai"]' \
  --query "Command.CommandId" \
  --output text
```

---

### Step 2 — Update Deploy Script

In `.github/workflows/deploy.yml`, update the SSM command to pull and deploy both repos.

**Current command (NY only):**
```
cd /home/ubuntu/utility-billing-ai && git fetch origin main && git checkout main && git reset --hard origin/main && bash scripts/fetch_secrets.sh && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build && docker compose ps
```

**Updated command (NY + VA):**
```
cd /home/ubuntu/utility-billing-ai && git fetch origin main && git checkout main && git reset --hard origin/main && bash scripts/fetch_secrets.sh && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build && cd /home/ubuntu/va-billing-ai && git fetch origin main && git reset --hard origin/main && docker compose up -d --build && docker compose -f /home/ubuntu/utility-billing-ai/docker-compose.yml ps
```

Commit and push this change to `Dev`, create PR, merge to `main`.

---

### Step 3 — Verify VA Containers Are On Correct Network

After first deploy run this via SSM:

```bash
aws ssm send-command \
  --instance-ids "i-0393dd4f827866db2" \
  --document-name "AWS-RunShellScript" \
  --region "us-east-2" \
  --parameters commands='["docker network inspect utility-billing-ai_default | grep -A3 va-"]' \
  --query "Command.CommandId" \
  --output text
```

Expected output — both VA containers listed in the network:
```
"utility-va-api": { ... }
"utility-va-streamlit": { ... }
```

If VA containers are NOT in the network, ask VA team to verify the `networks` section in their `docker-compose.yml`.

---

### Step 4 — Test

| URL | Expected Result |
|---|---|
| `http://3.12.193.9/` | Portal page with NY and VA cards |
| `http://3.12.193.9/` → New York Audit | NY dashboard loads |
| `http://3.12.193.9/va` | VA Streamlit app loads |

---

## Port Reference

| Service | Internal Port | Container Name |
|---|---|---|
| NY API | 8000 | `utility-api` |
| NY Streamlit | 8501 | `utility-streamlit` |
| VA API | 8001 | `utility-va-api` |
| VA Streamlit | 8502 | `utility-va-streamlit` |
| nginx | 80 (public) | `utility-billing-ai-nginx-1` |

---

## How Deploys Work After Integration

```
You push to NY main
        ↓
GitHub Actions triggers
        ↓
SSM runs on EC2:
  1. Pull NY code → rebuild NY containers
  2. Pull VA code → rebuild VA containers
        ↓
Both apps live, nginx routes traffic correctly
```

NY and VA codebases are fully independent.
A bug in VA never affects NY and vice versa.

---

## Troubleshooting

**502 Bad Gateway on `/va`**
VA containers are not running or not on the correct Docker network.
```bash
docker ps | grep va
docker network inspect utility-billing-ai_default | grep va
```

**VA containers keep getting overwritten**
Check that `profiles: [va]` exists on `va-api` and `va-streamlit` in `docker-compose.yml`.
NY deploy must never build VA images.

**nginx not routing `/va` correctly**
Check `nginx/nginx.conf` has the `/va` location block pointing to `va-streamlit:8501`.
Restart nginx via SSM if config was recently changed.
