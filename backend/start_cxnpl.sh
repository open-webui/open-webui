#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

# Set default values
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

# Check for TLS certificates
CERT_DIR="/var/shared/certs"
CERT_FILE="$CERT_DIR/tls.crt"
KEY_FILE_TLS="$CERT_DIR/tls.key"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE_TLS" ]; then
  echo "TLS certificates found, enabling HTTPS"
  UVICORN_OPTS="--ssl-keyfile $KEY_FILE_TLS --ssl-certfile $CERT_FILE"
  PROTOCOL="https"
else
  echo "No TLS certificates found, using HTTP only."
  UVICORN_OPTS=""
  PROTOCOL="http"
fi

PYTHON_CMD=$(command -v python3 || command -v python)

echo "Starting Open WebUI with custom configuration..."
echo "Protocol: $PROTOCOL"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Workers: ${UVICORN_WORKERS:-1}"

# Start with custom uvicorn arguments
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec "$PYTHON_CMD" -m uvicorn open_webui.main:app --log-level trace \
    --host "$HOST" \
    --port "$PORT" \
    --forwarded-allow-ips '*' \
    --workers "${UVICORN_WORKERS:-1}" \
    $UVICORN_OPTS
