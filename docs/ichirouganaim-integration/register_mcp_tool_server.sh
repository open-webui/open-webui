#!/usr/bin/env bash
# Registers an MCP server as a native open-webui Tool Server -- the
# built-in mechanism (backend/open_webui/routers/configs.py's
# /api/v1/configs/tool_servers endpoints) that makes an MCP server usable
# by *any* model in this instance, not just the claude_cli Pipe.
#
# This is a genuinely different mechanism from configure_mcp.sh:
# configure_mcp.sh sets claude_cli's own MCP_SERVER_URL Valve, which only
# that one Pipe function can use (the claude CLI subprocess connects
# directly, bypassing this fork's own MCP client entirely). This script
# instead registers the server in this fork's global tool_server.connections
# config, which native (non-claude-cli) models reach through
# backend/open_webui/utils/middleware.py's own MCPClient. The two are
# independent -- running both means the same MCP server is reachable two
# separate ways, which is fine, they don't conflict.
#
# What registering does NOT do by itself: make every model use it
# automatically. A chat still needs tool_ids containing
# "server:mcp:<server-id>" for a given request to actually connect and
# call it -- either via the model's own default-enabled tools (a separate,
# per-model config step, not done by this script) or the user picking it
# from the chat UI's "+" tools menu. This script only makes the connection
# exist and be selectable; verify_mcp_tool_server.sh (or SETUP.md's own
# guidance) confirms it actually connects.
#
# Idempotent: re-running with the same --id updates the existing entry in
# place (matched by info.id) rather than duplicating it.
#
# Usage:
#   export OPEN_WEBUI_API_KEY=sk-...
#   ./register_mcp_tool_server.sh --id ichirouganaim_mcp --url http://host.docker.internal:8931/mcp
#   ./register_mcp_tool_server.sh --id ichirouganaim_mcp --url <url> --name "Ichirouganaim MCP" --public
#
# --public grants read access to every user, via the exact shape
# has_access's own docstring documents for "public read"
# ({"principal_type": "user", "principal_id": "*", "permission": "read"}
# -- backend/open_webui/utils/access_control/__init__.py). Without it, a
# freshly registered connection with no access_grants defaults to
# admin-only (confirmed by reading has_connection_access directly, not
# assumed).
#
# Does not spend Claude usage -- registers and verifies the MCP server's
# own tool listing directly, no model invocation involved.

set -euo pipefail

BASE_URL="${OPEN_WEBUI_BASE_URL:-http://localhost:3000}"
API_KEY="${OPEN_WEBUI_API_KEY:?Set OPEN_WEBUI_API_KEY}"

SERVER_ID=""
MCP_URL=""
NAME=""
PUBLIC=false

while [ $# -gt 0 ]; do
  case "$1" in
    --id) SERVER_ID="$2"; shift 2 ;;
    --url) MCP_URL="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --public) PUBLIC=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$SERVER_ID" ] || [ -z "$MCP_URL" ]; then
  echo "Usage: register_mcp_tool_server.sh --id <server-id> --url <mcp-url> [--name <display name>] [--public]" >&2
  exit 1
fi
NAME="${NAME:-$SERVER_ID}"

echo "==> Fetching existing tool server connections..."
EXISTING="$(curl -sS "$BASE_URL/api/v1/configs/tool_servers" -H "Authorization: Bearer $API_KEY")"

echo "==> Building updated connection list (id=$SERVER_ID)..."
UPDATED="$(python3 -c "
import json, sys

existing = json.loads(sys.argv[1])
connections = existing.get('TOOL_SERVER_CONNECTIONS', [])

server_id = sys.argv[2]
url = sys.argv[3]
name = sys.argv[4]
public = sys.argv[5] == 'true'

new_conn = {
    'url': url,
    'path': '',
    'type': 'mcp',
    'auth_type': 'none',
    'headers': None,
    'key': None,
    'config': {'access_grants': [{'principal_type': 'user', 'principal_id': '*', 'permission': 'read'}] if public else []},
    'info': {'id': server_id, 'name': name},
}

connections = [c for c in connections if (c.get('info') or {}).get('id') != server_id]
connections.append(new_conn)

print(json.dumps({'TOOL_SERVER_CONNECTIONS': connections}))
" "$EXISTING" "$SERVER_ID" "$MCP_URL" "$NAME" "$PUBLIC")"

echo "==> Verifying the MCP server actually connects before saving (no Claude usage, direct MCP handshake)..."
VERIFY_PAYLOAD="$(python3 -c "
import json
print(json.dumps({
    'url': '$MCP_URL', 'path': '', 'type': 'mcp', 'auth_type': 'none',
    'headers': None, 'key': None, 'config': {}, 'info': {'id': '$SERVER_ID', 'name': '$NAME'},
}))
")"
VERIFY_RESULT="$(curl -sS -w '\n%{http_code}' -X POST "$BASE_URL/api/v1/configs/tool_servers/verify" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d "$VERIFY_PAYLOAD")"
VERIFY_STATUS="$(echo "$VERIFY_RESULT" | tail -1)"
VERIFY_BODY="$(echo "$VERIFY_RESULT" | sed '$d')"

if [ "$VERIFY_STATUS" != "200" ]; then
  echo "Error: verification failed (HTTP $VERIFY_STATUS): $VERIFY_BODY" >&2
  echo "Not saving the connection -- fix reachability first (this endpoint runs from inside the backend process itself, same network as the running container)." >&2
  exit 1
fi

TOOL_COUNT="$(echo "$VERIFY_BODY" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('specs',[])))" 2>/dev/null || echo "?")"
echo "    Verified -- MCP server responded, $TOOL_COUNT tool(s) discovered."

echo "==> Saving the connection..."
SAVE_RESULT="$(curl -sS -w '\n%{http_code}' -X POST "$BASE_URL/api/v1/configs/tool_servers" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d "$UPDATED")"
SAVE_STATUS="$(echo "$SAVE_RESULT" | tail -1)"
if [ "$SAVE_STATUS" != "200" ]; then
  echo "Error: saving the connection failed (HTTP $SAVE_STATUS): $(echo "$SAVE_RESULT" | sed '$d')" >&2
  exit 1
fi

echo "==> Done. Registered as tool_ids entry: server:mcp:$SERVER_ID"
if [ "$PUBLIC" = false ]; then
  echo "    Access is admin-only (no --public flag) -- only admin users can select or use this tool server."
fi
echo "    This makes it *available*, not automatically used by every model --"
echo "    a chat still needs tool_ids: [\"server:mcp:$SERVER_ID\"] to actually call it"
echo "    (the UI's '+' tools menu, or configuring it as a model's default tool)."
