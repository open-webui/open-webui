#!/usr/bin/env bash
set -euo pipefail
if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example -> .env and set ZAI_API_KEY"
  exit 1
fi
docker compose --env-file .env -f docker-compose.openwebui.yml up -d
echo "Open WebUI: http://localhost:3000"
