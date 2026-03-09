# Production Security Setup (EC2 + Docker Compose)

This guide keeps the backend API private while exposing Streamlit over HTTPS.

## 1) Run Compose with production override

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit
```

This binds ports to localhost only:
- API: `127.0.0.1:8000`
- Streamlit: `127.0.0.1:8501`
- Airflow: `127.0.0.1:8080`

## 2) Put Caddy in front for HTTPS

```bash
cp Caddyfile.example Caddyfile
# Edit Caddyfile and set app.yourdomain.com + email

docker run -d --name caddy \
  -p 80:80 -p 443:443 \
  -v "$PWD/Caddyfile:/etc/caddy/Caddyfile" \
  -v caddy_data:/data \
  -v caddy_config:/config \
  --restart unless-stopped \
  caddy:2
```

## 3) DNS

Point `app.yourdomain.com` A/AAAA record to the EC2 public IP or Elastic IP.

## 4) EC2 security group rules

Allow inbound only:
- TCP 22 from your admin IP
- TCP 80 from 0.0.0.0/0
- TCP 443 from 0.0.0.0/0

Do not open 8000, 8501, 8080 in the EC2 security group.

## 5) Verify API is private

From your laptop:

```bash
curl -I http://<EC2_PUBLIC_IP>:8000
```

Expected: connection refused or timeout.

From EC2 host:

```bash
curl -sS http://127.0.0.1:8000/api/v1/health/live
```

Expected: healthy response.

## 6) App-to-API path

Keep `API_BASE_URL=http://api:8000` in `.env.docker` for Docker internal calls.

## 7) Secrets and credentials

- Keep real values only in `.env.docker` on the server.
- Do not commit secrets.
- Rotate leaked keys immediately.

## 8) Optional hardening

- Add HTTP basic auth or SSO in front of Streamlit.
- Enable fail2ban for SSH.
- Restrict outbound rules if possible.
- Add regular OS patching cadence.
