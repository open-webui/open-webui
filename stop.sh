#!/usr/bin/env bash
# (c) IMT - Information Management Technology AG, CH-9470 Buchs, www.imt.ch.

set -euo pipefail

if [ "$#" -ne 0 ]; then
	echo "Usage: $0" >&2
	exit 1
fi

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [ -n "$(docker ps -aq --filter "label=com.docker.compose.project=open-webui")" ] ||
	[ -n "$(docker network ls -q --filter "label=com.docker.compose.project=open-webui")" ]; then
	if [ ! -f .env ]; then
		echo "Missing required environment file: .env" >&2
		exit 1
	fi
	compose=(docker compose)
	if [ -n "${LOCAL_COMPOSE_FILE:-}" ]; then
		compose+=(-f "$LOCAL_COMPOSE_FILE" --project-directory .)
	fi
	"${compose[@]}" --env-file .env -p open-webui down --remove-orphans
fi
