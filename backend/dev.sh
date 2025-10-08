
# Use correct Python if PYTHON312_HOME is set
if [ -n "$PYTHON312_HOME" ]; then
  export PATH="$PYTHON312_HOME:$PATH"
fi


export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
PORT="${PORT:-8080}"
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --reload
