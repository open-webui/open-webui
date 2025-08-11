#!/usr/bin/env bash
set -euo pipefail

# Generate the Python client for the NENNA.ai PII API using openapi-python-client
# Mirrors the TS generator target at https://api.nenna.ai/latest/openapi.json

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAGE_DIR="$ROOT_DIR/.openapi-python-client"
CONFIG_FILE="$ROOT_DIR/openapi-python-client-config.yml"
OPENAPI_URL="https://api.nenna.ai/latest/openapi.json"

command -v openapi-python-client >/dev/null 2>&1 || {
  echo "openapi-python-client is not installed. Install with: python3 -m pip install --user openapi-python-client" >&2
  exit 1
}

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

openapi-python-client generate \
  --url "$OPENAPI_URL" \
  --config "$CONFIG_FILE" \
  --output-path "$STAGE_DIR" \
  --overwrite

DEST_DIR="$ROOT_DIR/backend/open_webui/clients/nenna_pii_client"
rm -rf "$DEST_DIR"
mkdir -p "$(dirname "$DEST_DIR")"
cp -R "$STAGE_DIR/nenna_pii_client" "$DEST_DIR"

echo "Python client generated at $DEST_DIR"

