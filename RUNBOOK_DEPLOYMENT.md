# Deployment Runbook (API + Streamlit)

This runbook covers only two services:

1. FastAPI backend (`api`) - internal service for Streamlit
2. Streamlit frontend (`streamlit`) - internet-facing app

Airflow is intentionally out of scope in this guide.

---

## 1) Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- A valid `.env` file in project root (compose already reads `.env`)
- Ports available on local machine:
	- `8000` for API
	- `8501` for Streamlit

---

## 2) Local Docker Test (First Step)

### Start only API + Streamlit

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

### Open UI

- http://127.0.0.1:8501

### Stop services

```bash
docker compose down
```

---

## 3) Production Topology (Target)

Desired traffic flow:

- User browser -> Streamlit (public)
- Streamlit -> API (`http://api:8000` on Docker network)
- API is not publicly reachable

Implementation pattern on one EC2 host:

- API binds to `127.0.0.1:8000`
- Streamlit binds to `127.0.0.1:8501`
- Caddy reverse proxy exposes only Streamlit on `443`

---

## 4) Environment Variables You Must Set

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
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (if not using IAM role)

Notes:

- Keep `.env` only on server. Never commit secrets.
- If deploying on EC2 with instance IAM role, static AWS keys can be omitted.

---

## 5) Troubleshooting Quick Checks

### API keeps restarting

```bash
docker compose logs --tail=200 api
```

### Streamlit can’t fetch backend

1. Confirm API health endpoint responds.
2. Confirm `API_BASE_URL=http://api:8000` in `.env`.
3. Restart services:

```bash
docker compose up -d --build api streamlit
```

### Clean restart

```bash
docker compose down
docker compose up -d --build api streamlit
```

---

## 6) Related Docs

- `documentation/DEPLOYMENT.md` - single local + AWS deployment guide
