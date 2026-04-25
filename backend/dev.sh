export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:3001"
export WEBUI_AUTH=False
export ENABLE_SIGNUP=True
PORT="${PORT:-3001}"
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload
