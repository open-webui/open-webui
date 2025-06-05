PORT="${PORT:-8080}"

RAG_LOG_LEVEL=DEBUG
MAIN_LOG_LEVEL=DEBUG
CONFIG_LOG_LEVEL=DEBUG

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload