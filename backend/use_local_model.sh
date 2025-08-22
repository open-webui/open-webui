#!/usr/bin/env bash
# filepath: /Users/jiaqiyi/Documents/NAGA-open-webui/backend/use_local_model.sh

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

# 🔑 KEY SETTINGS TO ALLOW ALL USERS TO USE LOCAL MODELS
# Disable model restrictions
export ENABLE_MODEL_FILTER=false
export MODEL_FILTER_ENABLED=false

# Allow non-admin users to access models
export ENABLE_ADMIN_EXPORT=false
export ENABLE_ADMIN_CHAT_ACCESS=false

# Enable local model access for all users
export ENABLE_LOCAL_WEB_FETCH=true
export ENABLE_RAG_LOCAL_WEB_LOADER=true

# Optional: Set default models that all users can see
export DEFAULT_MODELS="tinyllama:latest,deepseek-r1:1.5b"

# User permissions - Allow all users to use models
export DEFAULT_USER_ROLE="user"
export ENABLE_SIGNUP=true
export ENABLE_LOGIN_FORM=true

# Model access permissions
export MODELS_ACCESS_ALL_USERS=true
export OLLAMA_MODELS_ACCESS_ALL=true

# WebUI Secret Key
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
echo "  🔓 MODEL_FILTER_ENABLED: $MODEL_FILTER_ENABLED"
echo "  👥 Models accessible to all users: YES"
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
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --reload