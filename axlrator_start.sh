#!/bin/bash

mkdir -p ~/log

# --- 1. RAG Server ---
if pgrep -f "python -m app.server" > /dev/null; then
    echo "[RAG] Already running. Skipping..."
else
    echo "[RAG] Starting..."
    cd ~/rag_server
    source venv/bin/activate
    nohup python -m app.server > ~/log/rag_server_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
fi

# --- 2. Backend ---
if pgrep -f "start.sh" > /dev/null; then
    echo "[Backend] Already running. Skipping..."
else
    echo "[Backend] Starting..."
    cd ~/aifred-openwebui/backend
    source venv/bin/activate
    nohup ./start.sh > ~/log/backend_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
fi

# --- 3. Frontend ---
if pgrep -f "vite preview" > /dev/null; then
    echo "[Frontend] Already running. Skipping..."
else
    echo "[Frontend] Starting..."
    cd ~/aifred-openwebui/frontend
    nohup npm run preview -- --host 0.0.0.0 > ~/log/frontend_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
fi