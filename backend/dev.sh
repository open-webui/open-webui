PORT="${PORT:-8080}"
# ../venv/bin/python -m uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload
../venv/bin/python -m debugpy --listen 5678 -m uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload