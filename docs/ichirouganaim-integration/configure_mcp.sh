#!/usr/bin/env bash
# Reliably wires (or re-wires) the claude_cli Pipe's MCP_SERVER_URL Valve
# -- the one config change that activates MCP tool access (SETUP.md step
# 8). Packages that step as a script instead of hand-typed curl commands,
# so it's the same repeatable operation whether it's the first time this
# is set up, or re-confirming it after a container recreation, a Valve
# accidentally getting cleared, or moving to a new machine.
#
# Verifies reachability *from inside the container* before setting
# anything -- SETUP.md's own step 8 warns not to assume that based on it
# working from the host, since they're genuinely different network paths
# (confirmed live earlier this session: a URL reachable from the host can
# still be unreachable from inside the container's own network namespace).
# Then sets the Valve, reads it back to confirm the write actually took,
# and reports the final state -- never trusts "the API call didn't error"
# alone as proof it worked.
#
# Usage:
#   export OPEN_WEBUI_API_KEY=sk-...
#   ./configure_mcp.sh http://host.docker.internal:8931/mcp
#   ./configure_mcp.sh ""              # clear it -- disables MCP tool access
#   OPEN_WEBUI_BASE_URL=http://localhost:8080 ./configure_mcp.sh <url>
#
# Does NOT spend any Claude usage by itself -- this only touches the
# Valve config, no `claude` CLI invocation happens here. Pair with a real
# chat afterward (SETUP.md step 9, or concurrency_test.sh) to confirm
# tool-calling actually works end to end, which does spend usage.

set -euo pipefail

MCP_URL="${1-}"
if [ $# -eq 0 ]; then
  echo "Usage: configure_mcp.sh <mcp-server-url>   (pass \"\" to clear/disable MCP)" >&2
  exit 1
fi

BASE_URL="${OPEN_WEBUI_BASE_URL:-http://localhost:3000}"
API_KEY="${OPEN_WEBUI_API_KEY:?Set OPEN_WEBUI_API_KEY}"
CONTAINER="${OPEN_WEBUI_CONTAINER:-open-webui}"

if [ -n "$MCP_URL" ]; then
  echo "==> Checking '$CONTAINER' can reach $MCP_URL (from inside the container, not just the host)..."
  if ! docker exec "$CONTAINER" true 2>/dev/null; then
    echo "Error: container '$CONTAINER' isn't running or isn't reachable." >&2
    exit 1
  fi
  # Checked separately from the command substitution, not via `cmd || echo
  # FAIL` inside it -- confirmed live that pattern is broken here: curl
  # prints "000" to stdout on a connection failure *and* exits non-zero,
  # so `$(cmd || echo FAIL)` concatenates both into "000FAIL", which then
  # matched neither exact-string check below and silently let a bad URL
  # through. Capturing the exit status via $? right after, instead of
  # inside the substitution, avoids that.
  set +e
  HTTP_CODE="$(docker exec "$CONTAINER" curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$MCP_URL" 2>/dev/null)"
  CURL_STATUS=$?
  set -e
  if [ "$CURL_STATUS" -ne 0 ] || [ "$HTTP_CODE" = "000" ] || [ -z "$HTTP_CODE" ]; then
    echo "Error: '$CONTAINER' cannot reach $MCP_URL at all (connection failure, not just a non-2xx status)." >&2
    echo "If the MCP server runs on the same host machine outside Docker, use http://host.docker.internal:<port>/... instead of localhost -- localhost inside the container means the container itself, not the host." >&2
    exit 1
  fi
  echo "    Reachable (HTTP $HTTP_CODE — any real status code, even a 4xx, confirms the network path works)."
else
  echo "==> Clearing MCP_SERVER_URL (disables MCP tool access, plain chat keeps working)..."
fi

echo "==> Setting the Valve..."
curl -sS -X POST "$BASE_URL/api/v1/functions/id/claude_cli/valves/update" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"MCP_SERVER_URL\":\"$MCP_URL\"}" \
  -o /dev/null -w "    HTTP %{http_code}\n"

echo "==> Reading the Valve back to confirm the write actually took..."
ACTUAL="$(curl -sS "$BASE_URL/api/v1/functions/id/claude_cli/valves" -H "Authorization: Bearer $API_KEY")"
echo "    $ACTUAL"

READBACK_URL="$(echo "$ACTUAL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('MCP_SERVER_URL',''))" 2>/dev/null || echo "PARSE_FAILED")"
if [ "$READBACK_URL" != "$MCP_URL" ]; then
  echo "Error: Valve readback ('$READBACK_URL') doesn't match what was set ('$MCP_URL') -- the write may not have taken." >&2
  exit 1
fi

echo "==> Done. MCP_SERVER_URL is now: '${MCP_URL:-<empty, disabled>}'"
echo "    This does NOT confirm tool-calling actually works end to end -- send a"
echo "    real chat that needs a tool call (SETUP.md step 9, or concurrency_test.sh)"
echo "    to verify that, which spends real Claude usage unlike this script."
