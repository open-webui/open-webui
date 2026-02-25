#!/bin/bash
# Safe deploy script — never uses --delete on backend
set -e

SERVER="chat-aws"
REMOTE_BASE="/home/ubuntu/open-webui"

echo "=== Building frontend ==="
npm run build

echo "=== Syncing frontend build (no --delete) ==="
rsync -az build/ "$SERVER:$REMOTE_BASE/build/"

echo "=== Syncing backend Python files (no --delete) ==="
# Only sync .py files — never delete anything on the server
rsync -az --include="*.py" --include="*/" --exclude="*" \
  backend/open_webui/ "$SERVER:$REMOTE_BASE/backend/open_webui/"

echo "=== Restarting service ==="
ssh "$SERVER" "sudo systemctl restart openwebui"

echo "=== Done ==="
