#!/usr/bin/env bash
# deploy.sh — Deploy chat.jawafdehi.org stack
#
# Run from within the monal host (/opt/openwebui).
# Pulls the latest compose file, custom Python overrides, and static
# assets from the jawafdehi-main branch, then restarts the Docker stack.
#
# Usage (on monal-instance1):
#   cd /opt/openwebui && ./deploy.sh
#
# Requires:
#   - Docker and docker compose
#   - mcp.env and .env configured
#   - gcloud authenticated for gcplogs driver (owui-log-writer@newnepal2)

set -euo pipefail

BRANCH="${BRANCH:-jawafdehi-main}"
REPO_BASE="https://raw.githubusercontent.com/Jawafdehi/open-webui/${BRANCH}/deploy/chat"

echo "=== Deploying chat.jawafdehi.org (branch: ${BRANCH}) ==="

# Pull latest deployment files from the repo
echo "--- Updating compose file ---"
curl -sSfL -o docker-compose.prod.yml "${REPO_BASE}/docker-compose.prod.yml"

echo "--- Updating custom Python overrides ---"
mkdir -p custom
curl -sSfL -o custom/middleware.py    "${REPO_BASE}/custom/middleware.py"
curl -sSfL -o custom/tools_utils.py   "${REPO_BASE}/custom/tools_utils.py"
curl -sSfL -o custom/tools_models.py  "${REPO_BASE}/custom/tools_models.py"

echo "--- Updating static assets ---"
mkdir -p static
for f in apple-touch-icon.png custom.css favicon-96x96.png favicon-dark.png \
         favicon.ico favicon.png favicon.svg logo.png site.webmanifest \
         splash-dark.png splash.png web-app-manifest-192x192.png \
         web-app-manifest-512x512.png; do
  curl -sSfL -o "static/${f}" "${REPO_BASE}/static/${f}"
done

echo "--- Updating env templates (if not already present) ---"
test -f .env.example   || curl -sSfL -o .env.example   "${REPO_BASE}/.env.example"
test -f mcp.env.example || curl -sSfL -o mcp.env.example "${REPO_BASE}/mcp.env.example"

# Pull latest Docker image
echo "--- Pulling latest image ---"
docker pull "jawafdehi/open-webui:${BRANCH}"

# Redeploy
echo "--- Redeploying ---"
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "=== Deploy complete ==="
echo "Verify: curl -s https://chat.jawafdehi.org/ | head -5"
