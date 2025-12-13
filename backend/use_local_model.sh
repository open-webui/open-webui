#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

echo "🚀 Starting Open WebUI with Local Models for All Users"
echo "=================================================="

# Ollama Configuration
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_API_BASE_URL="http://localhost:11434"
export ENABLE_OLLAMA_API=true

# Server Configuration
export PORT=8080
export HOST=0.0.0.0

# 🔑 CRITICAL: This is the key environment variable from env.py line 385
export BYPASS_MODEL_ACCESS_CONTROL=true

# WebUI Secret Key (required)
KEY_FILE=.webui_secret_key
if test "$WEBUI_SECRET_KEY $WEBUI_JWT_SECRET_KEY" = " "; then
  echo "Loading WEBUI_SECRET_KEY from file..."
  
  if ! [ -e "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
  fi
  
  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

echo "Configuration:"
echo "  🤖 OLLAMA_BASE_URL: $OLLAMA_BASE_URL"
echo "  ✅ ENABLE_OLLAMA_API: $ENABLE_OLLAMA_API"
echo "  🔓 BYPASS_MODEL_ACCESS_CONTROL: $BYPASS_MODEL_ACCESS_CONTROL"
echo "  👥 All users can access local models: YES"
echo "  🌐 Server: $HOST:$PORT"
echo ""

# Check if Ollama is running
echo "🔍 Checking Ollama connection..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running and accessible"
    echo "📋 Available models:"
    curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | sed 's/^/  - /'
else
    echo "❌ Ollama is not running or not accessible"
    echo "   Please start Ollama first: ollama serve"
    exit 1
fi

echo ""
echo "🚀 Starting Open WebUI backend..."
echo "   Frontend will be available at: http://localhost:5173"
echo "   Backend API docs at: http://localhost:8080/docs"
echo ""

# Start the server
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec python -m uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --reload