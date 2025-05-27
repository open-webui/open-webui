source .env
PORT="${PORT:-3030}"
ENV=dev uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload --log-level info

