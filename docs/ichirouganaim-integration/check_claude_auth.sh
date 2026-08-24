#!/usr/bin/env bash
# Checks whether the claude CLI inside the running container is still
# logged in -- the OAuth session can be invalidated by things outside this
# deployment's control (the Claude.ai subscription lapsing, revoking the
# session from Claude.ai's own account settings, a forced re-auth for a
# security reason). This script can only detect that, not fix it: the fix
# is a human running `claude auth login` again through a real browser,
# same as initial setup (SETUP.md step 7) -- there's no way to script
# around a login that genuinely requires a person's own OAuth grant.
#
# Never modifies anything -- safe to run on a schedule (cron, a monitoring
# system's own scheduler, etc) purely to get an early warning instead of
# discovering it the next time someone tries to chat.
#
# Usage:
#   ./check_claude_auth.sh
#   OPEN_WEBUI_CONTAINER=my-container ./check_claude_auth.sh
#
# Exit code: 0 if logged in, 1 otherwise (including "container not
# running" -- treated as a failure state, not silently skipped).

set -euo pipefail

CONTAINER="${OPEN_WEBUI_CONTAINER:-open-webui}"

if ! docker exec "$CONTAINER" true 2>/dev/null; then
  echo "ALERT: container '$CONTAINER' isn't running or isn't reachable." >&2
  exit 1
fi

STATUS_JSON="$(docker exec "$CONTAINER" claude auth status 2>/dev/null || true)"

if [ -z "$STATUS_JSON" ]; then
  echo "ALERT: couldn't get auth status from '$CONTAINER' (empty response -- claude CLI may be missing or broken)." >&2
  exit 1
fi

LOGGED_IN="$(python3 -c "
import json, sys
try:
    print(json.loads(sys.argv[1]).get('loggedIn', False))
except Exception:
    print(False)
" "$STATUS_JSON")"

if [ "$LOGGED_IN" = "True" ]; then
  echo "OK: claude CLI is logged in. ($STATUS_JSON)"
  exit 0
else
  echo "ALERT: claude CLI is NOT logged in. ($STATUS_JSON)" >&2
  echo "Fix: docker exec -it $CONTAINER claude auth login" >&2
  exit 1
fi
