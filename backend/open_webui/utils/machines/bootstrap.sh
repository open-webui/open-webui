# Sent over SSH stdin by utils/machines/ssh.py. Tokens (__OPEN_WEBUI_*__) are validated before rendering.
# Output lines starting with OPEN_WEBUI: drive the progress UI; everything else is log.
set -eu
ROOT="$HOME/.open-webui/__OPEN_WEBUI_ID__"
VERSION="__OPEN_WEBUI_VERSION__"

echo "OPEN_WEBUI:step:detect"
case "$(uname -s) $(uname -m)" in
  "Linux x86_64"|"Linux aarch64"|"Darwin arm64") ;;
  *) echo "OPEN_WEBUI:error:Unsupported system: $(uname -sm)"; exit 2 ;;
esac
command -v curl >/dev/null 2>&1 || { echo "OPEN_WEBUI:error:curl is required on the machine"; exit 2; }
command -v tar >/dev/null 2>&1 || { echo "OPEN_WEBUI:error:tar is required on the machine"; exit 2; }
mkdir -p "$ROOT/run"
chmod 700 "$ROOT" "$ROOT/run"
echo "OPEN_WEBUI:root:$ROOT"

echo "OPEN_WEBUI:step:install"
export UV_INSTALL_DIR="$ROOT/bin" UV_TOOL_DIR="$ROOT/tools" UV_TOOL_BIN_DIR="$ROOT/bin" \
       UV_PYTHON_INSTALL_DIR="$ROOT/python" UV_CACHE_DIR="$ROOT/cache" UV_NO_MODIFY_PATH=1
if [ ! -x "$ROOT/bin/uv" ]; then
  curl -LsSf "https://astral.sh/uv/__OPEN_WEBUI_UV_VERSION__/install.sh" | sh >/dev/null
fi
if [ "$(cat "$ROOT/version" 2>/dev/null || true)" != "$VERSION" ]; then
  if [ -x "$ROOT/stop.sh" ]; then "$ROOT/stop.sh"; fi
  "$ROOT/bin/uv" tool install --quiet --force --python 3.12 "open-terminal==$VERSION"
  "$ROOT/bin/open-terminal" --version >/dev/null   # prove it runs here before recording it
  echo "$VERSION" > "$ROOT/version"
fi

echo "OPEN_WEBUI:step:configure"
umask 077
printf '%s' '__OPEN_WEBUI_API_KEY__' > "$ROOT/api-key"

cat > "$ROOT/start.sh" <<'EOF'
#!/bin/sh
# Idempotent: returns once our server is accepting on api.sock. Called on every tunnel open,
# possibly by several Open WebUI workers at once; exactly one of them launches the server.
ROOT="$(cd "$(dirname "$0")" && pwd)"
SOCK="$ROOT/run/api.sock"
MATCH="open-terminal run --ipc $SOCK"
ours() { ps -ww -eo pid=,args= 2>/dev/null | awk -v m="$MATCH" 'index($0, m) && $2 !~ /(^|\/)awk$/ {print $1}'; }
ready() { [ -S "$SOCK" ] && [ -n "$(ours)" ]; }
wait_ready() { i=0; while [ $i -lt 300 ]; do ready && return 0; sleep 0.1; i=$((i+1)); done; return 1; }

ready && exit 0
i=0
until mkdir "$ROOT/start.lock" 2>/dev/null; do
  holder="$(cat "$ROOT/start.lock/pid" 2>/dev/null || true)"
  if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then rm -rf "$ROOT/start.lock"; continue; fi
  ready && exit 0                       # another worker finished launching it
  i=$((i+1)); [ $i -lt 600 ] || { echo "start.sh: timed out waiting for lock" >&2; exit 1; }
  sleep 0.1
done
echo $$ > "$ROOT/start.lock/pid"
trap 'rm -rf "$ROOT/start.lock"' EXIT
if [ -z "$(ours)" ]; then               # nothing running: launch (a running server just needs time)
  rm -f "$SOCK"
  cd "$HOME"
  OPEN_TERMINAL_API_KEY_FILE="$ROOT/api-key" nohup "$ROOT/bin/open-terminal" run \
    --ipc "$SOCK" >>"$ROOT/server.log" 2>&1 </dev/null &
  echo $! > "$ROOT/pid"
fi
wait_ready || { echo "start.sh: server did not come up, see $ROOT/server.log" >&2; tail -20 "$ROOT/server.log" >&2; exit 1; }
EOF

cat > "$ROOT/stop.sh" <<'EOF'
#!/bin/sh
# Stops every server bound to *our* socket path (the path contains the machine id, so this
# never touches another install or a process that merely reused a PID).
ROOT="$(cd "$(dirname "$0")" && pwd)"
MATCH="open-terminal run --ipc $ROOT/run/api.sock"
ours() { ps -ww -eo pid=,args= 2>/dev/null | awk -v m="$MATCH" 'index($0, m) && $2 !~ /(^|\/)awk$/ {print $1}'; }
pids="$(ours)"
[ -n "$pids" ] && kill $pids 2>/dev/null
i=0; while [ -n "$(ours)" ] && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
pids="$(ours)"; [ -n "$pids" ] && kill -9 $pids 2>/dev/null
rm -f "$ROOT/pid" "$ROOT/run/api.sock"
exit 0
EOF

chmod 700 "$ROOT/start.sh" "$ROOT/stop.sh"

echo "OPEN_WEBUI:step:start"
"$ROOT/start.sh"
echo "OPEN_WEBUI:ready:$VERSION"
