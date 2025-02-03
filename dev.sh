#!/bin/bash

# 创建日志目录
mkdir -p logs
nvm use 18
# 启动前端，将输出重定向到日志文件
nohup npm run dev > logs/frontend.log 2>&1 &

# 进入 backend 目录并运行 start.sh，将输出重定向到日志文件
cd backend && nohup ./start.sh > ../logs/backend.log 2>&1 &

echo "Services started in background. Check logs/ directory for output."
echo "Frontend log: logs/frontend.log"
echo "Backend log: logs/backend.log"
