#!/bin/bash

cd "$(dirname "$0")"

PORT="${PORT:-8080}"
GLOBAL_LOG_LEVEL=debug
ENV=dev

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload