#!/bin/bash
# setup_autostart.sh
# Run once on EC2 to install the systemd service that auto-fetches SSM secrets
# and starts Docker Compose on every boot (including after Lambda-triggered starts).
#
# Usage (on EC2):
#   chmod +x scripts/setup_autostart.sh
#   sudo ./scripts/setup_autostart.sh

set -euo pipefail

APP_DIR="/home/ubuntu/utility-billing-ai"

chmod +x "$APP_DIR/scripts/fetch_secrets.sh"
chmod +x "$APP_DIR/scripts/fetch_and_start.sh"

cat > /etc/systemd/system/utility-billing-startup.service << EOF
[Unit]
Description=Fetch SSM secrets and start Utility Billing Docker Compose
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=$APP_DIR
ExecStart=/bin/bash $APP_DIR/scripts/fetch_and_start.sh
RemainAfterExit=yes
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable utility-billing-startup.service

echo "Autostart service installed and enabled."
echo "On next boot, EC2 will automatically:"
echo "  1. Fetch latest secrets from SSM Parameter Store"
echo "  2. Write fresh .env"
echo "  3. Start Docker Compose (api + streamlit + nginx)"
