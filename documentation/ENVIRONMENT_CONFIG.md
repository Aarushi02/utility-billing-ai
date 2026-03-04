# Environment Configuration Guide

## 1) Environment Files Strategy

Use separate env files by runtime mode:

- `.env.local` → local venv/manual runs
- `.env.docker` → docker compose runs
- `.env.prod` → production server or secret manager

Example templates are available in project root:

- `.env.local.example`
- `.env.docker.example`
- `.env.prod.example`

This split avoids accidental cross-mode hostnames (for example using `localhost` in Docker where service DNS should be `api`, `airflow`, `postgres`).

---

## 2) Variable Resolution

The app uses `get_env()` from `src/utils/config.py`.

Resolution order:

1. Streamlit Secrets (when available)
2. OS environment variables
3. `.env` values loaded by runtime
4. default value in code

---

## 3) Required Core Variables

### Authentication

- `LOGIC_USERNAME`
- `LOGIC_PASSWORD`
- `SECRET_KEY`

### Database

- `DB_TYPE` (`postgres` or `sqlite`)
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

### API Routing

- `API_BASE_URL` (used by Streamlit to call backend API)

### Airflow Integration

- `AIRFLOW_API_URL` (should include `/api/v2`)
- `AIRFLOW_API_USER`
- `AIRFLOW_API_PASSWORD`
- `AIRFLOW_DAG_ID`

### Optional External Services

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_BUCKET_NAME`
- `AWS_REGION`

---

## 4) Runtime-Specific Examples

### Local (venv)

- `API_BASE_URL=http://127.0.0.1:8000`
- `AIRFLOW_API_URL=http://127.0.0.1:8080/api/v2`
- `DB_HOST=127.0.0.1` (or managed DB host)

Start stack with helper script:

```bash
./run_local_stack.sh start
```

### Docker Compose

- `API_BASE_URL=http://api:8000`
- `AIRFLOW_API_URL=http://airflow:8080/api/v2`
- `DB_HOST=postgres`

Compose reads `.env.docker` via `env_file` in `docker-compose.yml`.

### Production

- `API_BASE_URL=https://api.yourdomain.com`
- `AIRFLOW_API_URL=http://airflow.internal:8080/api/v2`
- `DB_HOST=<managed-db-host>`

---

## 5) Security Rules

- Do not commit real secrets.
- Rotate exposed keys immediately.
- Keep Airflow credentials only in backend/API runtime, not in frontend-only systems.
- Prefer secret manager for production (`.env.prod` should be template-only in git).

---

## 6) Troubleshooting

### `Read timed out` in Streamlit

- Check backend health: `curl http://127.0.0.1:8000/api/v1/health/live`
- Confirm `API_BASE_URL` matches running backend URL
- Restart stack: `./run_local_stack.sh restart`

### API starts but Airflow trigger returns `502`

- Check `AIRFLOW_API_URL`
- Confirm Airflow is reachable and credentials are valid

### Swagger unavailable

- Verify API process is live on port 8000
- Open `http://127.0.0.1:8000/docs`
