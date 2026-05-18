#!/usr/bin/env bash
# deploy.sh — Deploy chat.jawafdehi.org stack
#
# Supports two modes:
#   CI mode:   bundle is pre-copied to /tmp/openwebui-deploy/ by GitHub Actions
#   Manual:    run from /opt/openwebui (pulls files from jawafdehi-main branch)
#
# Usage:
#   CI (via GitHub Actions deploy-chat.yml):
#     Post-build: bundle lands in /tmp/openwebui-deploy/; this script syncs to /opt/openwebui
#   Manual (on monal-instance1):
#     cd /opt/openwebui && ./bin/deploy.sh
#
# Requires:
#   - Docker and docker compose
#   - mcp.env and .env configured
#   - gcloud authenticated for gcplogs driver (owui-log-writer@newnepal2)

set -euo pipefail

BRANCH="${BRANCH:-jawafdehi-main}"
TARGET="/opt/openwebui"
BUNDLE="/tmp/openwebui-deploy"
SECRETS_DIR="/opt/openwebui-secrets"

echo "=== Deploying chat.jawafdehi.org (branch: ${BRANCH}) ==="

# Detect mode: CI push vs manual pull
if [ -d "${BUNDLE}/bin" ] && [ -f "${BUNDLE}/docker-compose.prod.yml" ]; then
  echo "--- CI mode: syncing bundle from ${BUNDLE} ---"

  # Verify bundle integrity
  echo "--- Verifying bundle ---"
  for f in \
    docker-compose.prod.yml \
    custom/middleware.py \
    custom/tools_utils.py \
    custom/tools_models.py \
    static/favicon.ico \
    static/logo.png; do
    if [ ! -f "${BUNDLE}/${f}" ]; then
      echo "ERROR: missing bundle file: ${f}" >&2
      exit 1
    fi
  done
  echo "  Bundle verified."

  # Preserve secrets before replacing target
  echo "--- Preserving secrets ---"
  mkdir -p "${SECRETS_DIR}"
  for f in .env mcp.env; do
    if [ -f "${TARGET}/${f}" ]; then
      cp -p "${TARGET}/${f}" "${SECRETS_DIR}/${f}"
      echo "  Saved ${f} → ${SECRETS_DIR}/${f}"
    elif [ ! -f "${SECRETS_DIR}/${f}" ]; then
      echo "  WARNING: ${f} not found in ${TARGET} or ${SECRETS_DIR} — deploy may fail"
    fi
  done

  # Sync bundle to target (preserve data volume, secrets are external)
  echo "--- Syncing to ${TARGET} ---"
  rsync -av --delete \
    --exclude='/.env' \
    --exclude='/mcp.env' \
    --exclude='/data' \
    --exclude='/venv' \
    "${BUNDLE}/" "${TARGET}/"

  # Restore secrets (if not already provided by external secrets dir)
  for f in .env mcp.env; do
    if [ -f "${SECRETS_DIR}/${f}" ] && [ ! -f "${TARGET}/${f}" ]; then
      cp -p "${SECRETS_DIR}/${f}" "${TARGET}/${f}"
      echo "  Restored ${f} from ${SECRETS_DIR}"
    fi
  done

  echo "  Sync complete."

else
  # Manual mode: pull from GitHub raw
  echo "--- Manual mode: pulling from GitHub raw ---"
  REPO_BASE="https://raw.githubusercontent.com/Jawafdehi/open-webui/${BRANCH}/deploy/chat"

  echo "--- Updating compose file ---"
  curl -sSfL -o "${TARGET}/docker-compose.prod.yml" "${REPO_BASE}/docker-compose.prod.yml"

  echo "--- Updating custom Python overrides ---"
  mkdir -p "${TARGET}/custom"
  curl -sSfL -o "${TARGET}/custom/middleware.py"    "${REPO_BASE}/custom/middleware.py"
  curl -sSfL -o "${TARGET}/custom/tools_utils.py"   "${REPO_BASE}/custom/tools_utils.py"
  curl -sSfL -o "${TARGET}/custom/tools_models.py"  "${REPO_BASE}/custom/tools_models.py"

  echo "--- Updating static assets ---"
  mkdir -p "${TARGET}/static"
  for f in apple-touch-icon.png custom.css favicon-96x96.png favicon-dark.png \
           favicon.ico favicon.png favicon.svg logo.png site.webmanifest \
           splash-dark.png splash.png web-app-manifest-192x192.png \
           web-app-manifest-512x512.png; do
    curl -sSfL -o "${TARGET}/static/${f}" "${REPO_BASE}/static/${f}"
  done

  echo "--- Updating env templates (if not already present) ---"
  test -f "${TARGET}/.env.example"   || curl -sSfL -o "${TARGET}/.env.example"   "${REPO_BASE}/.env.example"
  test -f "${TARGET}/mcp.env.example" || curl -sSfL -o "${TARGET}/mcp.env.example" "${REPO_BASE}/mcp.env.example"
fi

# Pull latest Docker image
echo "--- Pulling latest image ---"
docker pull "jawafdehi/open-webui:${BRANCH}"

# Redeploy
echo "--- Redeploying ---"
cd "${TARGET}"
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "=== Deploy complete ==="
echo "Verify: curl -s https://chat.jawafdehi.org/ | head -5"
