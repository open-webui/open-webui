#!/usr/bin/env bash
# (c) IMT - Information Management Technology AG, CH-9470 Buchs, www.imt.ch.

set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [ "$#" -ne 0 ]; then
	echo "Usage: $0" >&2
	exit 1
fi

docker build \
	--build-arg BUILD_HASH="$(git rev-parse HEAD 2>/dev/null || echo dev-build)" \
	-t open-webui:local -f Dockerfile .
