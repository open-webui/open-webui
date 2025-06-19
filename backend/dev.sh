export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
PORT="${PORT:-8080}"
uvicorn open_webui.main:app --port $PORT --host localhost --forwarded-allow-ips '*' --reload