# Beginner Deployment Guide (No Domain, No Lambda)

This is the simplest path to go live for one organization.

## Goal

- Internet access to Streamlit UI
- API not exposed publicly
- No domain required
- Test locally first, then move to AWS EC2

## Important files

- Base compose: `docker-compose.yml`
- Simple override: `docker-compose.simple.yml`
- Env file used by compose: `.env.docker`

If your real values are in `.env` only, run:

```bash
cp .env .env.docker
```

Then edit `.env.docker` and confirm these values:

- `API_BASE_URL=http://api:8000`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `OPENAI_API_KEY` (if used)
- AWS keys (if used)

---

## Part A: Local Docker test

### 1) Start containers

```bash
docker compose -f docker-compose.yml -f docker-compose.simple.yml up -d --build api streamlit
```

### 2) Check status

```bash
docker compose ps
```

### 3) Test URLs on your laptop

- Streamlit: `http://127.0.0.1:8501`
- API health from host only: `http://127.0.0.1:8000/api/v1/health/live`

### 4) Verify API is not public on LAN

Because API is bound to `127.0.0.1`, only the host can access it.

---

## Part B: Move to AWS EC2 (no domain)

### 1) Create EC2

- Ubuntu 22.04
- Instance type: `t3.small` (or `t3.micro` for very light usage)
- Attach Elastic IP (recommended)

### 2) EC2 security group inbound rules

- `22` from your IP only
- `8501` from your office IP(s) or trusted IP(s)

Do NOT open:
- `8000`
- `8080`

### 3) Install Docker on EC2

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

### 4) Deploy app on EC2

```bash
git clone <your-repo-url>
cd utility-billing-ai
cp .env .env.docker   # if needed
# edit .env.docker

docker compose -f docker-compose.yml -f docker-compose.simple.yml up -d --build api streamlit
```

### 5) Access app from internet

Open in browser:

```text
http://<EC2_PUBLIC_IP>:8501
```

---

## Security notes (for this no-domain setup)

- API stays private (`127.0.0.1:8000` only).
- Streamlit is public on port `8501`.
- Restrict `8501` in security group to trusted IP ranges (best for single entity).
- Keep secrets in `.env.docker` on server only.

---

## Cost saving (single-entity usage)

- Stop EC2 when not in use.
- Start EC2 when needed.

You can manually stop/start from AWS Console and pay much less.

---

## When to upgrade later

Use domain + HTTPS reverse proxy (Caddy/Nginx) when:
- You want TLS without browser warnings
- Multiple users access over internet
- You need cleaner URL like `app.company.com`
