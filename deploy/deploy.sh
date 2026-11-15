#!/usr/bin/env bash
# Run on the VPS after a GitHub Actions image build. No git reset or shared stack changes.
set -euo pipefail

: "${CHAT_IMAGE:?Expected immutable ghcr.io/...@sha256:... image}"
[[ "$CHAT_IMAGE" =~ ^ghcr\.io/g-cat-devs/chat-gcat@sha256:[a-f0-9]{64}$ ]] || {
  echo 'Refusing unexpected/unpinned image' >&2; exit 1;
}
cd /opt/chat-gcat
[[ -f .env.production ]] || { echo 'Create /opt/chat-gcat/.env.production first' >&2; exit 1; }
[[ "$(stat -c '%a' .env.production)" == 600 ]] || {
  echo '.env.production must have mode 600' >&2; exit 1;
}
if grep -q 'REPLACE_WITH_RANDOM_SECRET' .env.production; then
  echo 'Set a real WEBUI_SECRET_KEY before deployment' >&2; exit 1
fi
export CHAT_IMAGE
previous=$(docker inspect --format '{{.Config.Image}}' chat1-webui 2>/dev/null || true)
if [[ -n "$previous" && "$previous" != "$CHAT_IMAGE" ]]; then
  echo "Previous image: $previous"
fi
docker pull "$CHAT_IMAGE"
compose=(docker compose -f compose.production.yml)
# Server-owned migration overrides must survive image deployments and rollbacks.
if [[ -f compose.production.override.yml ]]; then
  compose+=(-f compose.production.override.yml)
fi
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps webui
ok=false
for attempt in $(seq 1 36); do
  if [[ "$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8089/health 2>/dev/null || true)" == 200 ]] &&
     [[ "$(docker inspect --format '{{.Config.Image}}' chat1-webui 2>/dev/null || true)" == "$CHAT_IMAGE" ]] &&
     [[ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' chat1-webui 2>/dev/null || true)" == healthy ]]; then
    ok=true
    break
  fi
  sleep 5
done
if [[ "$ok" != true ]]; then
  docker logs --tail 60 chat1-webui >&2 || true
  if [[ -n "$previous" && "$previous" != "$CHAT_IMAGE" ]]; then
    echo "Health failed; rolling back to $previous" >&2
    CHAT_IMAGE="$previous" "${compose[@]}" up -d --no-deps webui
    for attempt in $(seq 1 24); do
      if [[ "$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8089/health 2>/dev/null || true)" == 200 ]] &&
         [[ "$(docker inspect --format '{{.Config.Image}}' chat1-webui 2>/dev/null || true)" == "$previous" ]]; then
        echo 'Previous image restored and responding' >&2
        exit 1
      fi
      sleep 5
    done
    echo 'Rollback did not recover health; intervention required' >&2
  fi
  exit 1
fi
echo "chat1 healthy on image $CHAT_IMAGE"
