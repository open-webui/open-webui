#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/canchat-v2

if [ ! -f package.json ]; then
  echo "CANChat package.json not found." >&2
  exit 1
fi

echo "Installing CANChat frontend dependencies..."
npm ci --ignore-scripts

echo "Creating Python virtual environment..."
if [ ! -f .venv/bin/activate ]; then
  python3 -m venv .venv
fi

echo "CANChat development environment initialized."
echo "Start frontend: npm run dev -- --port 5173"
echo "Start backend: bash .devcontainer/terms/start-backend.sh"