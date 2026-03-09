# Utility Billing AI - Deployment

This is the single deployment guide for local testing first, then AWS production.

## A) Local Docker (Step 1)

### Start API + Streamlit

```bash
docker compose up -d --build api streamlit
```

### Verify

```bash
docker compose ps
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
```

Expected:

1. API health returns `{"status":"ok"}`
2. Streamlit returns `200`

Swagger URL:

- `http://127.0.0.1:8000/docs`

Stop:

```bash
docker compose down
```

## B) AWS Production (Step 2)

Target behavior:

1. Streamlit is publicly reachable.
2. API is private/internal for Streamlit only.

### Services used

1. EC2
2. Security Group
3. Elastic IP
4. IAM Role
5. S3

### Deploy commands on EC2

```bash
git clone <repo-url>
cd utility-billing-ai
# create .env with production values

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api streamlit
```

### Security group inbound

Allow:

1. 22 (your IP)
2. 80 (internet)
3. 443 (internet)

Do not allow:

1. 8000
2. 8501
3. 8080

### Reverse proxy

Use Caddy/Nginx in front of Streamlit for public HTTPS.

## C) Environment Variables (minimum)

Required:

1. `LOGIC_USERNAME`
2. `LOGIC_PASSWORD`
3. `DB_TYPE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
4. `API_BASE_URL=http://api:8000` (container-to-container)

Optional:

1. `OPENAI_API_KEY`, `OPENAI_MODEL`
2. `AWS_BUCKET_NAME`, `AWS_REGION`
3. `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (prefer IAM role on EC2)

## D) Common Commands

Rebuild and restart:

```bash
docker compose up -d --build api streamlit
```

View logs:

```bash
docker compose logs --tail=200 api
docker compose logs --tail=200 streamlit
```

Full cleanup and recreate:

```bash
docker compose down --remove-orphans
docker compose up -d --build api streamlit
```
