PORT="${PORT:-8080}"
# Add the parent directory to the Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)/..
uvicorn main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload