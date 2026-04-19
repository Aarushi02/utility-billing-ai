#!/bin/bash
# fetch_and_start.sh
# Runs on every EC2 boot (via systemd) — fetches latest secrets from SSM,
# then starts Docker Compose. This ensures credentials are always current
# even after the Lambda scheduler starts a stopped instance.

set -euo pipefail

export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

APP_DIR="/home/ubuntu/utility-billing-ai"
LOG="/var/log/fetch-and-start.log"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) boot startup ===" >> "$LOG"

cd "$APP_DIR"

echo "Fetching secrets from SSM..." >> "$LOG"
bash scripts/fetch_secrets.sh >> "$LOG" 2>&1

echo "Starting Docker Compose..." >> "$LOG"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d >> "$LOG" 2>&1

echo "Done." >> "$LOG"
