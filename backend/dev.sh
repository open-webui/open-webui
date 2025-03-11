PORT="${PORT:-8080}"
python -m functions.installation
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload