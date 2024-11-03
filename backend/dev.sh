PORT="${PORT:-8080}"
hypercorn open_webui.main:app --bind "$HOST:$PORT" --proxy-headers --reload
