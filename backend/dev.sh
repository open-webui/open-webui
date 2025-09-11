PORT="${PORT:-8080}"
export CORS_ALLOW_ORIGIN="http://localhost:5173"
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload