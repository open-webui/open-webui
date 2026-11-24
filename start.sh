#!/usr/bin/env bash
# (c) IMT - Information Management Technology AG, CH-9470 Buchs, www.imt.ch.

set -euo pipefail

if [ "$#" -ne 0 ]; then
	echo "Usage: $0" >&2
	exit 1
fi

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [ ! -f .env ]; then
	echo "Missing required environment file: .env" >&2
	exit 1
fi

compose=(docker compose)
if [ -n "${LOCAL_COMPOSE_FILE:-}" ]; then
	compose+=(-f "$LOCAL_COMPOSE_FILE" --project-directory .)
fi

"${compose[@]}" --env-file .env -p open-webui config --quiet

if [ -z "${LOCAL_COMPOSE_FILE:-}" ]; then
	docker network inspect traefik-public >/dev/null 2>&1 || docker network create traefik-public >/dev/null
fi

"${compose[@]}" --env-file .env -p open-webui up -d --wait --wait-timeout "${WAIT_TIMEOUT:-300}"
