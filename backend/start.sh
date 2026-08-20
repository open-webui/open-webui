#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Container entry point for Open WebUI.
# Handles secret key generation, optional Ollama/CUDA/Playwright setup,
# HuggingFace Space deployment, and launches the uvicorn server.
# ---------------------------------------------------------------------------

# Default optional env vars that we test below with bash's `,,` lowercase
# expansion. The two can't be combined inline (`${VAR:-default,,}` makes
# the default literal `,,`), so we normalise once up front and the simple
# `${VAR,,}` form stays safe under `set -u` everywhere else.
: "${WEB_LOADER_ENGINE:=}" "${USE_OLLAMA_DOCKER:=}" "${USE_CUDA_DOCKER:=}"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR" || exit 1

# ── Playwright browser installation (if configured) ──────────────────────────

if [[ "${WEB_LOADER_ENGINE,,}" == "playwright" ]]; then
  if [[ -z "${PLAYWRIGHT_WS_URL:-}" ]]; then
    echo "Installing Playwright Chromium browser..."
    playwright install chromium
    playwright install-deps chromium
  fi
  python -c "import nltk; nltk.download('punkt_tab')"
fi

# ── Secret key setup ─────────────────────────────────────────────────────────

# Where the generated key lives, in order of preference:
#   1. WEBUI_SECRET_KEY_FILE, if the operator set one
#   2. an existing, non-empty ./.webui_secret_key, so installs that already have
#      one keep it -- tested with -e, not -r, so that a key we cannot read is
#      still selected and fails loudly below rather than being quietly bypassed
#      in favour of a freshly generated one
#   3. DATA_DIR, which is the mounted volume
# This script cd's to its own directory, so for a container (2) resolves inside
# the image rather than on the volume: the key is lost whenever the container is
# recreated, which silently invalidates every session. That directory is also
# not writable when the container runs as a non-root or arbitrary UID
# (OpenShift's restricted SCC), and `set -e` then aborts the boot outright.
# DATA_DIR is read from the environment only. A value set solely in
# backend/.env is not visible here, and those deployments keep the old
# behaviour; this does not make them worse, it just does not fix them.
if [[ -n "${WEBUI_SECRET_KEY_FILE:-}" ]]; then
  KEY_FILE="$WEBUI_SECRET_KEY_FILE"
elif [[ -e .webui_secret_key && -s .webui_secret_key ]]; then
  KEY_FILE=".webui_secret_key"
else
  KEY_FILE="${DATA_DIR:-./data}/.webui_secret_key"
fi
WEBUI_SECRET_KEY_LENGTH="${WEBUI_SECRET_KEY_LENGTH:-24}"
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

if [[ -z "${WEBUI_SECRET_KEY:-}" && -z "${WEBUI_JWT_SECRET_KEY:-}" ]]; then
  echo "No WEBUI_SECRET_KEY environment variable set, loading from file."

  # Regenerate when the key is missing or empty, but deliberately NOT when it is
  # merely unreadable. An empty key is a reachable state -- an interrupted write
  # leaves one -- and on a volume it persists, so it would otherwise be loaded
  # as "" on every later boot and fail with a misleading "WEBUI_SECRET_KEY is
  # not set". A key we cannot read, on the other hand, may well be a perfectly
  # good one belonging to another UID or group, and it is also the default
  # encryption key for OAuth client info, OAuth session tokens and valves, so
  # replacing it would destroy data at rest rather than merely sign people out.
  # `-s` needs no read permission, so that case falls through to the `cat` below
  # and fails loudly, which is what stock does today.
  if [[ ! -s "$KEY_FILE" ]]; then
    echo "Generating new WEBUI_SECRET_KEY..."
    if ! [[ "$WEBUI_SECRET_KEY_LENGTH" =~ ^[1-9][0-9]*$ ]]; then
      echo "WEBUI_SECRET_KEY_LENGTH must be a positive integer." >&2
      exit 1
    fi
    # Resolve a symlink first so we replace its target, as the plain redirect
    # used to, rather than swapping out the operator's link for a regular file.
    if [[ -L "$KEY_FILE" ]]; then
      # readlink -f exits non-zero and silent when a parent component is missing
      # or the link is circular; say so rather than dying with no output.
      key_link="$KEY_FILE"
      KEY_FILE=$(readlink -f -- "$key_link") || {
        echo "Cannot resolve the symlink at $key_link." >&2
        exit 1
      }
    fi
    mkdir -p -- "$(dirname -- "$KEY_FILE")"
    # Write to a temporary file and rename so an interrupted write cannot leave
    # a half-written key behind. Only reached when the target is missing or
    # empty, so the rename never lands on a key worth keeping.
    # 0640, not 0600: the key lives on a volume that may be remounted under a
    # different arbitrary UID, and group 0 is the part OpenShift keeps stable.
    key_tmp=$(mktemp -- "$KEY_FILE.XXXXXX")
    trap 'rm -f -- "${key_tmp:-}"' EXIT
    head -c "$WEBUI_SECRET_KEY_LENGTH" /dev/random | base64 > "$key_tmp"
    chmod 640 -- "$key_tmp"
    mv -f -- "$key_tmp" "$KEY_FILE"
    trap - EXIT
  fi

  echo "Loading WEBUI_SECRET_KEY from ${KEY_FILE}"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

# ── Ollama (bundled Docker image) ────────────────────────────────────────────

if [[ "${USE_OLLAMA_DOCKER,,}" == "true" ]]; then
  echo "Starting bundled ollama serve..."
  ollama serve &
fi

# ── CUDA library paths ──────────────────────────────────────────────────────

if [[ "${USE_CUDA_DOCKER,,}" == "true" ]]; then
  echo "CUDA enabled — extending LD_LIBRARY_PATH for torch/cudnn libraries."
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
fi

# ── HuggingFace Space deployment ─────────────────────────────────────────────

if [[ -n "${SPACE_ID:-}" ]]; then
  echo "Configuring for HuggingFace Space deployment..."

  if [[ -n "${ADMIN_USER_EMAIL:-}" && -n "${ADMIN_USER_PASSWORD:-}" ]]; then
    echo "Creating admin user for Space..."
    WEBUI_SECRET_KEY="${WEBUI_SECRET_KEY:-}" \
      uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" &
    webui_pid=$!

    echo "Waiting for server to become healthy..."
    until curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; do
      sleep 1
    done

    echo "Registering admin user..."
    curl -sS -X POST "http://localhost:${PORT}/api/v1/auths/signup" \
      -H "Accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"${ADMIN_USER_EMAIL}\", \"password\": \"${ADMIN_USER_PASSWORD}\", \"name\": \"Admin\"}"

    echo "Restarting server..."
    kill "$webui_pid"
    wait "$webui_pid" 2>/dev/null || true
  fi

  export WEBUI_URL="${SPACE_HOST}"
fi

# ── Launch uvicorn ───────────────────────────────────────────────────────────

PYTHON_CMD=$(command -v python3 || command -v python)
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"

if [[ "$#" -gt 0 ]]; then
  ARGS=("$@")
else
  ARGS=(--workers "$UVICORN_WORKERS")
fi

exec env WEBUI_SECRET_KEY="${WEBUI_SECRET_KEY:-}" \
  "$PYTHON_CMD" -m uvicorn open_webui.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
    "${ARGS[@]}"
