#!/usr/bin/env bash
# Combines SETUP.md's steps 5 and 6: mint (or reuse) an admin API key, then
# sync the claude_cli Pipe with it. One command instead of two manual steps
# with a copy-pasted key in between -- the actual gap this closes is that
# copy-paste step, which is exactly where a manual run is likely to go
# wrong (wrong container name, stale key pasted from a previous attempt,
# etc).
#
# Requires: an admin account already exists (sign up once through the web
# UI first -- SETUP.md step 4). Safe to re-run -- see
# bootstrap_admin_api_key.py's own docstring for why (reuses an existing
# key by default instead of rotating it).
#
# Usage:
#   ./bootstrap.sh
#   OPEN_WEBUI_CONTAINER=my-container OPEN_WEBUI_BASE_URL=http://localhost:8080 ./bootstrap.sh
#   ./bootstrap.sh --rotate    # force a fresh API key instead of reusing one

set -euo pipefail

CONTAINER="${OPEN_WEBUI_CONTAINER:-open-webui}"
BASE_URL="${OPEN_WEBUI_BASE_URL:-http://localhost:3000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! docker exec "$CONTAINER" true 2>/dev/null; then
  echo "Error: container '$CONTAINER' isn't running or isn't reachable." >&2
  echo "Set OPEN_WEBUI_CONTAINER if it's not named 'open-webui'." >&2
  exit 1
fi

echo "==> Bootstrapping admin API key on '$CONTAINER'..."
docker cp "$SCRIPT_DIR/bootstrap_admin_api_key.py" "$CONTAINER:/app/backend/bootstrap_admin_api_key.py"
REMOTE_CMD="WEBUI_SECRET_KEY=\"\$WEBUI_SECRET_KEY\" python3 bootstrap_admin_api_key.py $*"
BOOTSTRAP_OUTPUT="$(docker exec -w /app/backend "$CONTAINER" bash -c "$REMOTE_CMD")"
docker exec "$CONTAINER" rm -f /app/backend/bootstrap_admin_api_key.py

echo "$BOOTSTRAP_OUTPUT"

if echo "$BOOTSTRAP_OUTPUT" | grep -q '^NO_ADMIN_USER_FOUND'; then
  echo "Error: no admin account exists yet. Sign up through the web UI first (SETUP.md step 4), then re-run this script." >&2
  exit 1
fi

API_KEY="$(echo "$BOOTSTRAP_OUTPUT" | sed -n 's/^API_KEY=//p')"
if [ -z "$API_KEY" ]; then
  echo "Error: couldn't find API_KEY in bootstrap output above -- something went wrong." >&2
  exit 1
fi

echo "==> Syncing claude_cli Pipe function against $BASE_URL..."
OPEN_WEBUI_BASE_URL="$BASE_URL" OPEN_WEBUI_API_KEY="$API_KEY" \
  python3 "$SCRIPT_DIR/sync_pipe.py" "$SCRIPT_DIR/claude_cli.py"

echo
echo "==> Done. Admin API key (save it -- needed for step 8's MCP Valve update, if you use it):"
echo "    $API_KEY"
