#!/bin/bash

# Configuration Paths
REPO_DIR="/home/yeet/OWUI/open-webui-repo"
BACKEND_DIR="$REPO_DIR/backend"

# Cleanup handler to kill background tasks on Ctrl+C
cleanup() {
    echo -e "\nStopping Open WebUI development environment..."
    # Terminate all background jobs started by this script
    kill $(jobs -p) 2>/dev/null
    exit 0
}
trap cleanup SIGINT

echo "========================================="
echo "Starting Open WebUI Dev Stack..."
echo "========================================="

# 1. Spin up the Python Backend in the background
echo "-> Starting Backend Server..."
cd "$BACKEND_DIR" || exit 1

# Activate virtual environment and launch uvicorn in the background using '&'
source venv/bin/activate
export WEBUI_SECRET_KEY="PcewH5DVsmjGb1lTEU6nzKv2SXAYp7h9J3CufiLqQRBOyN0rZo8ktFdM4WgxaI"
export RAG_EMBEDDING_ENGINE="ollama"
python3 -m uvicorn open_webui.main:app --port 8080 --reload --host 0.0.0.0 &

# Give uvicorn 3 seconds to spin up, bind to port 8080, and print initial logs
sleep 3

# 2. Spin up the Node/Svelte Frontend in the foreground
echo "-> Starting Frontend Compiler..."
cd "$REPO_DIR" || exit 1
npm run dev
