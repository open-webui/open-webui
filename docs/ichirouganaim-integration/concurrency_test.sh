#!/usr/bin/env bash
# Fires N genuinely concurrent chat completions at the real claude_cli
# Pipe through the real running instance, verifying both correctness
# (each request gets its own, uncrossed response) and stability (the
# container survives). Built to answer a real question: does this scale
# to concurrent users, and if it breaks, is that a code bug or a resource
# ceiling?
#
# Each request uses parent_id:null (no chat_id/id) so the server
# auto-provisions a fresh, unique chat per request -- this still gives
# claude_cli.py's __chat_id__ a real unique value each time, exercising
# the same concurrent sessions.json write path a multi-worker deployment
# would hit (see claude_cli.py's _update_sessions docstring and
# decisions.md's 2026-08-23 concurrency-testing entry for why that matters
# and what broke before it was fixed). Each prompt asks the model to echo
# back a unique token, so a response landing on the wrong request would be
# caught, not just "some response came back."
#
# Usage:
#   ./concurrency_test.sh N
#   OPEN_WEBUI_BASE_URL=http://localhost:8080 ./concurrency_test.sh 25
#
# Spends real Claude usage -- one real completion per concurrent request.
# Start small and work up (2, 5, 10, ...) rather than jumping straight to
# a large N -- see decisions.md for what happened on a memory-constrained
# machine at N=15/25 (the container itself crashed from resource
# exhaustion, not a code defect -- confirmed via the memory trace in that
# entry). This script samples the container's own memory/PID count for
# the duration of the run and prints the peak, so a crash is diagnosable
# without a separate manual `docker stats` session.

set -euo pipefail

N="${1:?Usage: concurrency_test.sh N}"
BASE_URL="${OPEN_WEBUI_BASE_URL:-http://localhost:3000}"
API_KEY="${OPEN_WEBUI_API_KEY:?Set OPEN_WEBUI_API_KEY}"
CONTAINER="${OPEN_WEBUI_CONTAINER:-open-webui}"
WORKDIR="$(mktemp -d)"

echo "=== Concurrency test: N=$N, workdir=$WORKDIR ==="

# Background memory/PID sampler -- gives a peak reading for the run
# without needing a second terminal watching `docker stats` by hand.
MEM_LOG="$WORKDIR/mem.log"
(
  while true; do
    docker stats --no-stream --format '{{.MemUsage}} {{.MemPerc}} {{.PIDs}}' "$CONTAINER" 2>/dev/null >> "$MEM_LOG" || echo "CONTAINER_UNREACHABLE" >> "$MEM_LOG"
    sleep 1
  done
) &
SAMPLER_PID=$!
disown "$SAMPLER_PID"  # suppress bash's own "Terminated" job-control notice when it's killed below
trap 'kill "$SAMPLER_PID" 2>/dev/null || true' EXIT

echo "--> Firing $N concurrent completions..."
START=$(date +%s)
REQUEST_PIDS=()
for i in $(seq 1 "$N"); do
  TOKEN="TOK-N${N}-${i}-$$-$(date +%s%N)"
  echo "$TOKEN" > "$WORKDIR/expected_$i.txt"
  (
    curl -sS -N -X POST "$BASE_URL/api/chat/completions" \
      -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
      -d "{\"model\":\"claude_cli\",\"parent_id\":null,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly and only this text, nothing else, no punctuation added: $TOKEN\"}],\"stream\":true}" \
      > "$WORKDIR/raw_$i.txt" 2> "$WORKDIR/err_$i.txt"
    echo "$?" > "$WORKDIR/exit_$i.txt"
  ) &
  REQUEST_PIDS+=("$!")
done
# Wait only on the request subshells, not the memory sampler -- a bare
# `wait` waits for *every* background job of this shell, including the
# sampler's own infinite `while true` loop, which never exits on its own
# and would deadlock the whole script. Confirmed live: this was a real
# hang, not a slow response -- see decisions.md.
for pid in "${REQUEST_PIDS[@]}"; do
  wait "$pid"
done
END=$(date +%s)
echo "--> All requests finished in $((END - START))s"

kill "$SAMPLER_PID" 2>/dev/null || true
trap - EXIT

echo "--> Verifying..."
PASS=0
FAIL=0
for i in $(seq 1 "$N"); do
  EXIT_CODE=$(cat "$WORKDIR/exit_$i.txt" 2>/dev/null || echo "MISSING")
  EXPECTED=$(cat "$WORKDIR/expected_$i.txt")
  CONTENT=$(python3 -c "
import json
content = ''
try:
    with open('$WORKDIR/raw_$i.txt') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('data:'):
                continue
            payload = line[len('data:'):].strip()
            if payload == '[DONE]':
                continue
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            choices = obj.get('choices', [])
            if choices:
                delta = choices[0].get('delta', {})
                content += delta.get('content', '') or ''
except FileNotFoundError:
    pass
print(content)
")
  if [ "$EXIT_CODE" = "0" ] && echo "$CONTENT" | grep -qF "$EXPECTED"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL #$i: exit=$EXIT_CODE expected='$EXPECTED' got='$CONTENT'"
  fi
done

echo "=== Result: $PASS/$N passed, $FAIL failed ==="

if [ -s "$MEM_LOG" ]; then
  echo "--> Container memory during this run:"
  cat "$MEM_LOG"
  if grep -q CONTAINER_UNREACHABLE "$MEM_LOG"; then
    echo "  NOTE: container became unreachable during the run -- likely crashed. Check: docker inspect $CONTAINER --format 'restartCount={{.RestartCount}}'"
  fi
fi

echo "--> sessions.json entry count after this run (bounded at 500, see MAX_SESSIONS in claude_cli.py):"
docker exec "$CONTAINER" python3 -c "
import json
try:
    with open('/app/backend/data/cache/functions/claude_cli/sessions.json') as f:
        sessions = json.load(f)
    print(f'{len(sessions)} entries')
except FileNotFoundError:
    print('not found')
" 2>/dev/null || echo "  (container unreachable, skipped)"

rm -rf "$WORKDIR"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
