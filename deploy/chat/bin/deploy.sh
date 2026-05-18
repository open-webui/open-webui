#!/usr/bin/env bash
# deploy.sh — Deploy chat.jawafdehi.org stack on monal-instance1
#
# Usage:
#   ./deploy.sh                    # deploy latest jawafdehi-main image
#   LOG_DRIVER=gcplogs ./deploy.sh # deploy with GCP Cloud Logging
#
# Requires:
#   - SSH access to monal-instance1
#   - Docker and docker compose on the target host
#   - mcp.env and .env configured on the target host

set -euo pipefail

SSH_HOST="${SSH_HOST:-monal-instance1}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/openwebui}"
COMPOSE_FILE="docker-compose.prod.yml"
BRANCH="${BRANCH:-jawafdehi-main}"
LOG_DRIVER="${LOG_DRIVER:-}"

echo "=== Deploying chat.jawafdehi.org (branch: ${BRANCH}) ==="

# Pull latest deploy files from the repo branch
echo "--- Updating deploy files from jawafdehi-main ---"
ssh "$SSH_HOST" "cd ${DEPLOY_DIR} && \
  curl -sSfL -o docker-compose.prod.yml https://raw.githubusercontent.com/Jawafdehi/open-webui/${BRANCH}/deploy/chat/docker-compose.prod.yml && \
  curl -sSfL -o docker-compose.gcplogs.yaml https://raw.githubusercontent.com/Jawafdehi/open-webui/${BRANCH}/deploy/chat/docker-compose.gcplogs.yaml"

# Pull latest Docker image
echo "--- Pulling latest image ---"
ssh "$SSH_HOST" "docker pull jawafdehi/open-webui:${BRANCH}"

# Restart the stack
if [ -n "$LOG_DRIVER" ]; then
  echo "--- Redeploying with gcplogs logging driver ---"
  ssh "$SSH_HOST" "cd ${DEPLOY_DIR} && docker compose -f ${COMPOSE_FILE} -f docker-compose.gcplogs.yaml up -d --remove-orphans"
else
  echo "--- Redeploying ---"
  ssh "$SSH_HOST" "cd ${DEPLOY_DIR} && docker compose -f ${COMPOSE_FILE} up -d --remove-orphans"
fi

echo "=== Deploy complete ==="
echo "Verify: curl -s https://chat.jawafdehi.org/ | head -5"
