#!/bin/bash

set -eo pipefail

. /etc/environment

COMPOSE_BASE_COMMAND="docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.api.yaml -f docker-compose.data.yaml -f docker-compose.customized.yaml"

function start_services {
	$COMPOSE_BASE_COMMAND up --remove-orphans --force-recreate
}

function stop_services {
	$COMPOSE_BASE_COMMAND down
}

if [ "$1" == "up" ]; then
	start_services
elif [ "$1" == "down" ]; then
	stop_services
else
	echo 1>&2 "$0: ERROR: invalid argument"
	exit 1
fi

