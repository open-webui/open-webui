echo "Python version:"
python --version

echo "Starting backend dev server..."
PORT="${PORT:-8080}"
uvicorn main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload