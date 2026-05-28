#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

required_vars=(
  WEBUI_SECRET_KEY
  ENABLE_GOOGLE_DRIVE_INTEGRATION
  GOOGLE_DRIVE_CLIENT_ID
  GOOGLE_DRIVE_API_KEY
)

get_env_value() {
  local key="$1"
  local value
  value=$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)
  value="${value%\'}"
  value="${value#\'}"
  value="${value%\"}"
  value="${value#\"}"
  printf '%s' "$value"
}

failed=0

for var in "${required_vars[@]}"; do
  value=$(get_env_value "$var")
  if [[ -z "$value" ]]; then
    echo "ERROR: $var is missing or empty in $ENV_FILE" >&2
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi

if [[ "$(get_env_value ENABLE_GOOGLE_DRIVE_INTEGRATION)" != "true" ]]; then
  echo "WARN: ENABLE_GOOGLE_DRIVE_INTEGRATION is not 'true'. Google Drive picker will remain disabled." >&2
fi

if [[ "$(get_env_value WEBUI_SECRET_KEY)" =~ ^(changeme|replace|secret|your-secret)$ ]]; then
  echo "WARN: WEBUI_SECRET_KEY looks like a placeholder. Generate a real value with: openssl rand -hex 32" >&2
fi

echo "OK: Google Drive OAuth env validation passed for $ENV_FILE"
