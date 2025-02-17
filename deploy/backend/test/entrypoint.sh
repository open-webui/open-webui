#!/bin/sh
export PYTHONPATH=/backend
uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --forwarded-allow-ips '*' --ws-ping-timeout 430 --ws-ping-interval 50