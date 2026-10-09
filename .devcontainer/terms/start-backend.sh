#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/canchat-v2

source .venv/bin/activate

export PYTHONPATH="${PWD}/backend:${PYTHONPATH:-}"

if ! python -c 'import uvicorn, open_webui' 2>/dev/null; then
  echo "Installing CANChat Python backend dependencies..."
  python -m pip install --upgrade pip
  python -m pip install -r backend/requirements.txt
fi

export PORT=8080

exec bash backend/dev.sh