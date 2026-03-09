# Deployment Runbook

## What `.env.docker` means

`.env.docker` is the environment file used by Docker services (`api`, `streamlit`, `airflow`).

It is separate from `.env` so that:
- local venv runs can keep using local host values,
- Docker runs can use container DNS names (`api`, `airflow`) while DB points to your managed PostgreSQL host,
- production secrets can stay in `.env.prod` (or secret manager).

---

## Quick Start (Docker, split services)

### 1) Prepare env file

```bash
cp .env.docker.example .env.docker
# or edit existing .env.docker directly
```

Required updates in `.env.docker`:
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `LOGIC_PASSWORD`
- `SECRET_KEY`
- `AIRFLOW_API_PASSWORD`
- `AIRFLOW__WEBSERVER__SECRET_KEY`
- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`
- (optional) `OPENAI_API_KEY`, AWS keys

### 2) Start all services

```bash
docker compose up --build -d
```

### 3) Check service status

```bash
docker compose ps
```

### 4) Verify live endpoints

- API health: `http://127.0.0.1:8000/api/v1/health/live`
- Swagger: `http://127.0.0.1:8000/docs`
- Streamlit: `http://127.0.0.1:8501`
- Airflow UI: `http://127.0.0.1:8080`

### 5) Basic API tests

```bash
curl http://127.0.0.1:8000/api/v1/health/live
curl "http://127.0.0.1:8000/api/v1/runs?limit=5"
curl http://127.0.0.1:8000/api/v1/bills/accounts
```

### 6) Stop

```bash
docker compose down
```

---

## Local (without Docker)

### One-command local stack (recommended)

```bash
./run_local_stack.sh start
./run_local_stack.sh status
./run_local_stack.sh logs
./run_local_stack.sh stop
```

This script starts API first, verifies health, then starts Streamlit and opens your browser.

**On Windows**: Use Git Bash or WSL to run the bash script:
```bash
# Git Bash (right-click in folder -> "Git Bash Here")
./run_local_stack.sh start

# Or Windows Terminal with Git Bash profile
cd d:\utility-billing-ai
./run_local_stack.sh start
```

---

### Manual setup (if you prefer separate terminals)

#### API

```bash
source venv/bin/activate
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

#### Streamlit

```bash
source venv/bin/activate
export API_BASE_URL=http://127.0.0.1:8000
python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

### Airflow trigger test through API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/airflow/dag-runs
```

---

## Production split deployment strategy

Deploy three services independently:

1. **Backend API** (`uvicorn src.api.main:app`)  
2. **Frontend Streamlit** (`streamlit run app/streamlit_app.py`)  
3. **Airflow** (webserver/scheduler + metadata DB)

Recommended traffic flow:
- Browser -> Streamlit
- Streamlit -> API (`API_BASE_URL=https://api.yourdomain.com`)
- API -> Airflow (`AIRFLOW_API_URL=http://airflow.internal:8080/api/v2`)

Why this is good:
- independent scaling/restarts,
- no direct Airflow credentials in frontend,
- safer network boundaries (Airflow can remain private).

---

## Notes

- `{"detail":"Not Found"}` on `/` is normal; use `/docs` or `/api/v1/...`.
- If API starts but airflow trigger returns `502`, check `AIRFLOW_API_URL` and Airflow service availability.
- If Streamlit pages fail, confirm API is running and `API_BASE_URL` is correct.

## Developer Extension

For adding new logic, new API endpoints, and new Streamlit pages, use:

- `documentation/DEVELOPER_EXTENSION_GUIDE.md`
