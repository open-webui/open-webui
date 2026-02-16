#!/usr/bin/env bash

set -euo pipefail

OUTPUT_PATH="${1:-artifacts/baselines/baseline-$(date +%Y%m%d).json}"
ENVIRONMENT="${BASELINE_ENVIRONMENT:-local-unix}"
STARTUP_COMMAND="${BASELINE_STARTUP_COMMAND:-}"
TEST_COMMAND="${BASELINE_TEST_COMMAND:-npm run -s test:frontend}"
SKIP_TESTS="${BASELINE_SKIP_TESTS:-false}"

get_commit_hash() {
  git rev-parse HEAD 2>/dev/null || echo "unknown"
}

measure_startup_ms() {
  local cmd="$1"
  if [[ -z "$cmd" ]]; then
    echo "null"
    return
  fi

  local start end diff
  start=$(date +%s%3N 2>/dev/null || python - <<'PY'
import time
print(int(time.time() * 1000))
PY
)

  if bash -lc "$cmd" >/dev/null 2>&1; then
    end=$(date +%s%3N 2>/dev/null || python - <<'PY'
import time
print(int(time.time() * 1000))
PY
)
    diff=$((end - start))
    echo "$diff"
  else
    echo "null"
  fi
}

get_cpu_percent() {
  if command -v top >/dev/null 2>&1; then
    local idle
    idle=$(top -bn1 2>/dev/null | awk -F',' '/Cpu\(s\)/ {for(i=1;i<=NF;i++){if($i ~ /id/){gsub(/[^0-9.]/,"",$i); print $i; exit}}}')
    if [[ -n "${idle:-}" ]]; then
      awk -v idle="$idle" 'BEGIN { printf "%.2f", (100 - idle) }'
      return
    fi
  fi
  echo "null"
}

get_ram_used_mb() {
  if command -v free >/dev/null 2>&1; then
    local used
    used=$(free -m | awk '/Mem:/ {print $3}')
    [[ -n "${used:-}" ]] && echo "$used" && return
  fi
  echo "null"
}

get_test_pass_rate() {
  local cmd="$1"
  local skip="$2"

  if [[ "$skip" == "true" || -z "$cmd" ]]; then
    echo "null"
    return
  fi

  if bash -lc "$cmd" >/dev/null 2>&1; then
    echo "100"
  else
    echo "0"
  fi
}

commit_hash="$(get_commit_hash)"
timestamp_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
startup_time_ms="$(measure_startup_ms "$STARTUP_COMMAND")"
cpu_percent="$(get_cpu_percent)"
ram_mb="$(get_ram_used_mb)"
test_pass_rate_percent="$(get_test_pass_rate "$TEST_COMMAND" "$SKIP_TESTS")"

mkdir -p "$(dirname "$OUTPUT_PATH")"

cat > "$OUTPUT_PATH" <<JSON
{
  "commit_hash": "${commit_hash}",
  "timestamp_utc": "${timestamp_utc}",
  "environment": "${ENVIRONMENT}",
  "metrics": {
    "startup_time_ms": ${startup_time_ms},
    "ram_mb": ${ram_mb},
    "cpu_percent": ${cpu_percent},
    "test_pass_rate_percent": ${test_pass_rate_percent}
  }
}
JSON

echo "BASELINE_WRITTEN=${OUTPUT_PATH}"
