#!/usr/bin/env bash
# deploy.sh — Deploy chat.jawafdehi.org stack (CI mode)
#
# Bundle is pre-copied to /tmp/openwebui-deploy-<datetime>/ by GitHub Actions
# via rsync. This script syncs the bundle to /opt/openwebui and redeploys.
#
# Host prerequisites (one-time):
#   sudo mkdir -p /opt/openwebui /opt/openwebui-secrets
#   sudo chown <deploy-user>:<deploy-user> /opt/openwebui /opt/openwebui-secrets
#   # place secrets in /opt/openwebui-secrets/:
#   #   .env, mcp.env, owui-log-writer.credentials.json
#   sudo gcloud auth application-default login --cred-file=/opt/openwebui-secrets/owui-log-writer.credentials.json --quiet
#   usermod -aG docker <deploy-user>

set -euo pipefail

TARGET="/opt/openwebui"
BUNDLE="${BUNDLE_DIR:-/tmp/openwebui-deploy}"
SECRETS_DIR="/opt/openwebui-secrets"
BRANCH="${BRANCH:-jawafdehi-main}"

die() { echo "ERROR: $*" >&2; exit 1; }

echo "=== Deploying chat.jawafdehi.org (branch: ${BRANCH}) ==="
echo "--- CI mode: syncing bundle from ${BUNDLE} ---"

# Preconditions
for d in "${TARGET}" "${SECRETS_DIR}"; do
  [ -d "$d" ] || die "${d} does not exist"
  [ -w "$d" ] || die "${d} is not writable by $(whoami)"
done

# Assert required secret files
echo "--- Checking secrets ---"
for f in .env mcp.env; do
  [ -f "${SECRETS_DIR}/${f}" ] || die "${SECRETS_DIR}/${f} required but missing"
done
echo "  Secrets OK."

# Verify bundle
echo "--- Verifying bundle ---"
for f in docker-compose.prod.yml custom/middleware.py custom/tools_utils.py custom/tools_models.py static/favicon.ico static/logo.png; do
  [ -f "${BUNDLE}/${f}" ] || die "missing bundle file: ${f}"
done
echo "  Bundle verified."

# Sync to target
echo "--- Syncing to ${TARGET} ---"
rsync -av --no-group \
  --exclude='/.env' \
  --exclude='/mcp.env' \
  --exclude='/data' \
  --exclude='/venv' \
  "${BUNDLE}/" "${TARGET}/"
  echo "  Sync complete."

# Pull image
echo "--- Pulling image ---"
docker pull "jawafdehi/open-webui:${BRANCH}"

# Redeploy
echo "--- Redeploying ---"
cd "${TARGET}"
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Bootstrap configs if script exists
BOOTSTRAP="${TARGET}/bin/bootstrap-config.sh"
if [ -x "${BOOTSTRAP}" ]; then
  echo "--- Bootstrapping configs ---"
  "${BOOTSTRAP}"
fi

echo "=== Deploy complete ==="
echo "Verify: curl -s https://chat.jawafdehi.org/ | head -5"
