#!/bin/bash
source .env
PORT="${PORT:-3030}"
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload