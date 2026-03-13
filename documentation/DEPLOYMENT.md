# Utility Billing AI - Deployment

This project uses a single `docker-compose.yml` for both local and cloud.

## A) Local Smoke Test

Start:

```bash
docker compose up -d --build api streamlit
```

Verify:

```bash
docker compose ps
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
```

Expected:

1. API health returns `{"status":"ok"}`
2. Streamlit returns `200`

Stop:

```bash
docker compose down
```

## B) EC2 Production (Single-VM)

Target behavior:

1. Streamlit is public on port 8501.
2. API is private on EC2 localhost only.
3. Airflow is private on EC2 localhost only.

`docker-compose.yml` is already configured for this:

1. API -> `127.0.0.1:8000:8000`
2. Airflow -> `127.0.0.1:8080:8080`
3. Streamlit -> `8501:8501`

### 1) AWS setup

1. Launch EC2 (Ubuntu 22.04+ recommended)
2. Attach Elastic IP
3. Attach IAM role if using S3

Security Group inbound:

1. `22` from your IP
2. `8501` from internet (or restrict to your office/VPN IP)

Do not open `8000` or `8080`.

### 2) Server bootstrap

```bash
sudo apt update
sudo apt install -y ca-certificates curl git

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
	$(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
	sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

### 3) Deploy app

```bash
git clone <repo-url>
cd utility-billing-ai
```

Create `.env` with production values.

Start stack:

```bash
docker compose up -d --build api streamlit airflow
```

Initialize schema/migrations:

```bash
docker compose exec api python -m src.database.init_db
```

### 4) Verify production

From EC2:

```bash
curl -sS http://127.0.0.1:8000/api/v1/health/live
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8501
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080
```

Expected:

1. API health returns `{"status":"ok"}`
2. Streamlit returns `200`
3. Airflow returns `200` only from localhost on EC2

From your laptop/browser:

1. `http://<EC2_PUBLIC_IP>:8501` works
2. `http://<EC2_PUBLIC_IP>:8000` should not be reachable
3. `http://<EC2_PUBLIC_IP>:8080` should not be reachable

## C) Required Environment Variables

Minimum:

1. `DB_TYPE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
2. `LOGIC_USERNAME`, `LOGIC_PASSWORD`
3. `API_BASE_URL=http://api:8000`

Recommended:

1. `OPENAI_API_KEY`, `OPENAI_MODEL`
2. `AWS_BUCKET_NAME`, `AWS_REGION`
3. Prefer IAM role over static AWS access keys on EC2

## D) Operate / Troubleshoot

Restart:

```bash
docker compose up -d --build api streamlit airflow
```

Logs:

```bash
docker compose logs --tail=200 api
docker compose logs --tail=200 streamlit
docker compose logs --tail=200 airflow
```

Recreate:

```bash
docker compose down --remove-orphans
docker compose up -d --build api streamlit airflow
```
