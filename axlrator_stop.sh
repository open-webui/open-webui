echo "[Stopping all servers by port...]"

# Helper function to stop a process by port
stop_by_port() {
    local PORT=$1
    local NAME=$2

    PID=$(lsof -ti tcp:$PORT)

    if [ -n "$PID" ]; then
        echo "[$NAME] Stopping (PID: $PID)..."
        kill -9 $PID
    else
        echo "[$NAME] Not running (port $PORT)."
    fi
}

# --- RAG Server (port 8000) ---
stop_by_port 8000 "RAG Server"

# --- Backend (port 8080) ---
stop_by_port 8080 "Backend"

# --- Frontend (port 4173, 5173) ---
stop_by_port 4173 "Frontend"
stop_by_port 5173 "Frontend"

echo "[All applicable servers stopped by port.]"
~