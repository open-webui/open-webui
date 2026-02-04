release: cd backend/open_webui && python -m alembic upgrade head
web: cd backend && uvicorn open_webui.main:app --host 0.0.0.0 --port $PORT
