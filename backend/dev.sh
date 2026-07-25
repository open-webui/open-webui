set -euo pipefail

# Load local dev environment (repo-root .lde.env), if present.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDE_ENV="${LDE_ENV:-${SCRIPT_DIR}/.lde.env}"
if [ -f "${LDE_ENV}" ]; then
  echo "==> Loading env from ${LDE_ENV}"
  set -a
  # shellcheck disable=SC1090
  . "${LDE_ENV}"
  set +a
else
  echo "==> No .lde.env found at ${LDE_ENV} (skipping)"
fi


echo "==> Creating MinIO bucket '${S3_BUCKET_NAME}' via container '${MINIO_CONTAINER}'"

if ! docker ps --format '{{.Names}}' | grep -qx "${MINIO_CONTAINER}"; then
  echo "ERROR: container '${MINIO_CONTAINER}' is not running." >&2
  echo "Start it with: docker compose -f docker-compose.external-services.yaml up -d" >&2
  exit 1
fi

docker exec "${MINIO_CONTAINER}" sh -c "
  mc alias set local ${MINIO_ENDPOINT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} >/dev/null &&
  mc mb --ignore-existing local/${S3_BUCKET_NAME} &&
  mc ls local
"

echo "==> Done. Bucket '${S3_BUCKET_NAME}' is ready."

# CORS_ALLOW_ORIGIN / WEBUI_SECRET_KEY / OLLAMA_BASE_URL now come from .lde.env
PORT="${PORT:-8080}"
# Watch only the source package. Without --reload-dir, uvicorn watches the whole
# CWD including DATA_DIR (data/uploads), so uploading a file — e.g. a *.py — would
# trip the reloader and restart the server. --reload-exclude is a belt-and-suspenders
# guard in case DATA_DIR is relocated under the source tree.
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --reload --reload-dir open_webui --reload-exclude 'data/*'
