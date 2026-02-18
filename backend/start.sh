#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

# Add conditional Playwright browser installation (bash 3.2–compatible lowercase check)
if [[ "$(echo "${WEB_LOADER_ENGINE:-}" | tr '[:upper:]' '[:lower:]')" == "playwright" ]]; then
    if [[ -z "${PLAYWRIGHT_WS_URL}" ]]; then
        echo "Installing Playwright browsers..."
        playwright install chromium
        playwright install-deps chromium
    fi

    python -c "import nltk; nltk.download('punkt_tab')"
fi

if [ -n "${WEBUI_SECRET_KEY_FILE}" ]; then
    KEY_FILE="${WEBUI_SECRET_KEY_FILE}"
else
    KEY_FILE=".webui_secret_key"
fi

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
if test "$WEBUI_SECRET_KEY $WEBUI_JWT_SECRET_KEY" = " "; then
  echo "Loading WEBUI_SECRET_KEY from file, not provided as an environment variable."

  if ! [ -e "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    # Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one.
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
  fi

  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

if [[ "$(echo "${USE_OLLAMA_DOCKER:-}" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
    echo "USE_OLLAMA is set to true, starting ollama serve."
    ollama serve &
fi

if [[ "$(echo "${USE_CUDA_DOCKER:-}" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
  echo "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
  export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
fi

# Check if SPACE_ID is set, if so, configure for space
if [ -n "$SPACE_ID" ]; then
  echo "Configuring for HuggingFace Space deployment"
  if [ -n "$ADMIN_USER_EMAIL" ] && [ -n "$ADMIN_USER_PASSWORD" ]; then
    echo "Admin user configured, creating"
    WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' &
    webui_pid=$!
    echo "Waiting for webui to start..."
    while ! curl -s "http://localhost:${PORT}/health" > /dev/null; do
      sleep 1
    done
    echo "Creating admin user..."
    curl \
      -X POST "http://localhost:${PORT}/api/v1/auths/signup" \
      -H "accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{ \"email\": \"${ADMIN_USER_EMAIL}\", \"password\": \"${ADMIN_USER_PASSWORD}\", \"name\": \"Admin\" }"
    echo "Shutting down webui..."
    kill $webui_pid
  fi

  export WEBUI_URL=${SPACE_HOST}
fi

PYTHON_CMD=$(command -v python3 || command -v python)
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"

# Verify Python and uvicorn are available
echo "Python command: $PYTHON_CMD"
echo "Python version: $($PYTHON_CMD --version 2>&1)"
echo "Checking uvicorn installation..."
if $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
    echo "✓ Uvicorn is available via import"
else
    echo "ERROR: uvicorn is not available. Checking Python path..."
    $PYTHON_CMD -c "import sys; print('Python path:', sys.path)" 2>&1
    echo "Checking installed packages..."
    $PYTHON_CMD -m pip list | grep -i uvicorn || echo "uvicorn not found in pip list"
    echo "Attempting to find uvicorn..."
    find /usr/local -name uvicorn 2>/dev/null | head -5
    echo "Attempting to install uvicorn as fallback..."
    $PYTHON_CMD -m pip install --no-cache-dir "uvicorn[standard]==0.40.0" || echo "Failed to install uvicorn"
    if ! $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
        echo "ERROR: uvicorn still not available after fallback install"
        exit 1
    fi
    echo "✓ Uvicorn installed via fallback"
fi
echo "Uvicorn is available."

# Run comprehensive dependency checker (automatically installs missing packages)
echo "Verifying critical packages..."
if $PYTHON_CMD /app/backend/check_dependencies.py 2>&1; then
    echo "✓ All critical packages verified"
else
    echo "WARNING: Some dependencies may be missing, but continuing..."
fi

# Run database migrations before starting the app
echo "Running database migrations..."

# Verify DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    exit 1
fi
echo "DATABASE_URL is set (host: $(echo $DATABASE_URL | cut -d@ -f2 | cut -d: -f1))"

# Change to alembic directory
cd /app/backend/open_webui || {
    echo "ERROR: Failed to cd to /app/backend/open_webui"
    echo "Contents of /app/backend:"
    ls -la /app/backend/
    exit 1
}

echo "Current directory: $(pwd)"
echo "Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

# Run migrations - show output, fail container if migrations fail
if ! $PYTHON_CMD -m alembic upgrade head; then
    echo "ERROR: Database migrations failed! Container will not start."
    echo "Attempting to show current alembic state:"
    $PYTHON_CMD -m alembic current 2>&1 || true
    exit 1
fi

echo "✓ Database migrations completed successfully"
cd /app/backend || exit

# If script is called with arguments, use them; otherwise use default workers
if [ "$#" -gt 0 ]; then
    ARGS=("$@")
else
    ARGS=(--workers "$UVICORN_WORKERS")
fi

# Run uvicorn with error handling
echo "Starting uvicorn on $HOST:$PORT..."
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec "$PYTHON_CMD" -m uvicorn open_webui.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --forwarded-allow-ips '*' \
    --log-level info \
    "${ARGS[@]}" || {
    echo "Uvicorn failed to start. Exit code: $?"
    exit 1
}