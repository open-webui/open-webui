#!/bin/bash

<<<<<<< HEAD
# 날짜 형식
DATE=$(date +"%Y%m%d_%H%M%S")

=======
# 스크립트 실행 디렉토리를 기준으로 경로 설정
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$BASE_DIR/log"
mkdir -p "$LOG_DIR"

# --- 1. RAG Server ---
# if pgrep -f "python -m app.server" > /dev/null; then
#     echo "[RAG] Already running. Skipping..."
# else
#     echo "[RAG] Starting..."
#     cd "$BASE_DIR/rag_server" || exit
#     source venv/bin/activate
#     nohup python -m app.server > "$LOG_DIR/rag_server_$(date +'%Y%m%d_%H%M%S').log" 2>&1 &
#     cd "$BASE_DIR" || exit
# fi

# # --- 2. Backend ---
# if pgrep -f "backend/start.sh" > /dev/null; then
#     echo "[Backend] Already running. Skipping..."
# else
#     echo "[Backend] Starting..."
#     cd "$BASE_DIR/axlrator-webui/backend" || exit
#     source venv/bin/activate
#     nohup ./start.sh > "$LOG_DIR/backend_$(date +'%Y%m%d_%H%M%S').log" 2>&1 &
#     cd "$BASE_DIR" || exit
# fi

# --- 3. Frontend ---
>>>>>>> main
echo "[Frontend] Starting..."
cd "$BASE_DIR" || exit
nohup npm run dev -- --host 0.0.0.0 > "$LOG_DIR/frontend_$(date +'%Y%m%d_%H%M%S').log" 2>&1 &
cd "$BASE_DIR" || exit

<<<<<<< HEAD
# 백엔드 포어그라운드 실행
echo "[Backend] Starting..."
/app/axlrator-webui/backend/start.sh

=======
# --- 4. Backend ---
echo "[Backend] Foreground Starting..."
cd "$BASE_DIR/backend" || exit
# ./start.sh # 포어그라운드 실행
nohup ./start.sh > "$LOG_DIR/backend_$(date +'%Y%m%d_%H%M%S').log" 2>&1 & # 백그라운드 실행
>>>>>>> main
