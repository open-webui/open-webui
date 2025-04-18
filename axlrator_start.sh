#!/bin/bash

# 날짜 형식
DATE=$(date +"%Y%m%d_%H%M%S")

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

