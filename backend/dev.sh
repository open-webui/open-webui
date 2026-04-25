#!/bin/bash
# Local dev backend — uses .venv so deps are isolated and reproducible
# First time: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV" ]; then
  echo "❌ No .venv found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:3001"
export WEBUI_AUTH=False
export ENABLE_SIGNUP=True
PORT="${PORT:-3001}"

exec "$VENV/bin/uvicorn" open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload
