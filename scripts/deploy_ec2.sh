#!/bin/bash
# deploy_ec2.sh
# Runs on EC2 via SSM during GitHub Actions deploys.
# Handles NY and VA deploys independently with health checks.

set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

NY_DIR="/home/ubuntu/utility-billing-ai"
VA_DIR="/home/ubuntu/va-billing-ai"

log()  { echo "[$(date -u +%H:%M:%SZ)] $*"; }
fail() { log "ERROR: $*"; exit 1; }

# ── NY deploy ─────────────────────────────────────────────────────────────────
log "=== NY deploy starting ==="
cd "$NY_DIR"
bash scripts/fetch_secrets.sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
log "=== NY deploy complete ==="

# ── NY health check ───────────────────────────────────────────────────────────
log "Checking NY containers..."
sleep 5
UNHEALTHY=$(docker compose -f docker-compose.yml -f docker-compose.prod.yml ps \
  --format "table {{.Name}}\t{{.State}}" | awk 'NR>1 && $2!="running" {print $1}')
if [ -n "$UNHEALTHY" ]; then
  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50
  fail "NY containers not running after deploy: $UNHEALTHY"
fi
log "NY containers healthy."

# ── VA deploy (optional) ──────────────────────────────────────────────────────
if [ ! -d "$VA_DIR" ]; then
  log "VA directory not found — skipping VA deploy"
  exit 0
fi

log "=== VA deploy starting ==="
cd "$VA_DIR"

VA_OLD=$(git rev-parse HEAD)
git fetch origin main
git reset --hard origin/main
VA_NEW=$(git rev-parse HEAD)

bash "${NY_DIR}/scripts/fetch_secrets.sh" prod .env  # reuses utility-billing-ai secrets — VA shares the same SSM vars

if [ "$VA_OLD" != "$VA_NEW" ]; then
  log "VA code changed ($VA_OLD → $VA_NEW) — rebuilding"
  docker compose -f docker-compose.prod.yml up -d --build backend frontend
else
  log "VA code unchanged — restarting containers"
  docker compose -f docker-compose.prod.yml up -d backend frontend
fi

# ── VA health check ───────────────────────────────────────────────────────────
sleep 5
UNHEALTHY=$(docker compose -f docker-compose.prod.yml ps \
  --format "table {{.Name}}\t{{.State}}" | awk 'NR>1 && $2!="running" {print $1}')
if [ -n "$UNHEALTHY" ]; then
  docker compose -f docker-compose.prod.yml logs --tail=50
  fail "VA containers not running after deploy: $UNHEALTHY"
fi

log "=== VA deploy complete ==="
