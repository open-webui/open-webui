#!/bin/bash

mkdir -p /app/log

# --- 1. RAG Server ---
# if pgrep -f "python -m app.server" > /dev/null; then
#     echo "[RAG] Already running. Skipping..."
# else
#     echo "[RAG] Starting..."
#     cd ~/rag_server
#     source venv/bin/activate
#     nohup python -m app.server > ~/log/rag_server_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
# fi

# --- 2. Backend ---
# if pgrep -f "start.sh" > /dev/null; then
#     echo "[Backend] Already running. Skipping..."
# else
    # echo "[Backend] Starting..."
    # cd /app/axlrator-webui/backend
    # source venv/bin/activate
    # nohup ./start.sh > /app/log/backend_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
# fi

# --- 3. Frontend ---
# if pgrep -f "vite preview" > /dev/null; then
#     echo "[Frontend] Already running. Skipping..."
# else
echo "[Frontend] Starting..."
#cd /app/axlrator-webui/frontend
cd /app/axlrator-webui
#source venv/bin/activate
nohup npm run dev -- --host 0.0.0.0 > /app/log/frontend_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
    #nohup npm run preview -- --host 0.0.0.0 > /app/log/frontend_$(date +'%Y%m%d_%H%M%S').log 2>&1 &
# fi

# 백엔드 포어그라운드 실행
echo "[Backend] Starting..."
/app/axlrator-webui/backend/start.sh

#exec /app/axlrator-webui/backend/start.sh > /app/log/backend_$(date +'%Y%m%d_%H%M%S').log 2>&1