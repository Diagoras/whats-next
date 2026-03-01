#!/usr/bin/env bash
set -euo pipefail

# Run as root on a fresh Debian/Ubuntu VPS.
# Usage: curl -sL https://raw.githubusercontent.com/Diagoras/whats-next/master/deploy/setup.sh | bash

APP_DIR=/opt/whats-next

# --- Install system deps ---
apt-get update
apt-get install -y curl git

# --- Install Caddy ---
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

# --- Install uv ---
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# --- Create app user ---
id -u whatsnext &>/dev/null || useradd -r -m -s /bin/bash whatsnext

# --- Clone repo ---
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR" && git pull
else
  git clone https://github.com/Diagoras/whats-next.git "$APP_DIR"
fi
chown -R whatsnext:whatsnext "$APP_DIR"

# --- Create .env file if missing ---
if [ ! -f "$APP_DIR/.env" ]; then
  cat > "$APP_DIR/.env" <<'ENVEOF'
TAKEOUT_URL=
OPENROUTESERVICE_API_KEY=
GOOGLE_MAPS_API_KEY=
ENVEOF
  chown whatsnext:whatsnext "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo ">>> Edit /opt/whats-next/.env with your keys, then re-run this script."
  exit 0
fi

# --- Install deps + load data ---
cd "$APP_DIR"
sudo -u whatsnext uv sync
sudo -u whatsnext bash scripts/load_data.sh
sudo -u whatsnext uv run python main.py ingest

# --- Install systemd service ---
cp deploy/whatsnext.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now whatsnext

# --- Configure Caddy ---
echo ">>> Copy deploy/Caddyfile to /etc/caddy/Caddyfile, replacing YOURDOMAIN."
echo ">>> Then: systemctl reload caddy"
echo ""
echo "Done! App running at http://127.0.0.1:8000"
