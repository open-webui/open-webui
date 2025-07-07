#!/bin/bash

# 날짜 형식
DATE=$(date +"%Y%m%d_%H%M%S")

echo "[Frontend] Starting..."
cd "$BASE_DIR" || exit
nohup npm run dev -- --host 0.0.0.0 > "$LOG_DIR/frontend_$(date +'%Y%m%d_%H%M%S').log" 2>&1 &
cd "$BASE_DIR" || exit

echo "[Backend] Starting..."
/app/axlrator-webui/backend/start.sh


# 백엔드 포어그라운드 실행
echo "[Backend] Starting..."
/app/axlrator-webui/backend/start.sh

