#!/usr/bin/env bash

# Uvicorn 프로세스 찾기 및 종료
WEBUI_PID=$(ps aux | grep "uvicorn open_webui.main:app" | grep -v grep | awk '{print $2}')
OLLAMA_PID=$(ps aux | grep "ollama serve" | grep -v grep | awk '{print $2}')

# Open WebUI 종료
if [ -n "$WEBUI_PID" ]; then
  echo "Stopping Open WebUI (PID: $WEBUI_PID)..."
  kill "$WEBUI_PID"
else
  echo "Open WebUI is not running."
fi

# Ollama 종료 (옵션)
if [ -n "$OLLAMA_PID" ]; then
  echo "Stopping Ollama (PID: $OLLAMA_PID)..."
  kill "$OLLAMA_PID"
else
  echo "Ollama is not running."
fi

# 강제 종료 (필요 시)
sleep 2
if ps -p "$WEBUI_PID" > /dev/null 2>&1; then
  echo "Force stopping Open WebUI..."
  kill -9 "$WEBUI_PID"
fi

if ps -p "$OLLAMA_PID" > /dev/null 2>&1; then
  echo "Force stopping Ollama..."
  kill -9 "$OLLAMA_PID"
fi

echo "All processes stopped."
