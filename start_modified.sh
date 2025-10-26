#!/bin/bash

# Start Modified OpenWebUI with Token Usage Tracking and Reasoning Effort
# This script ensures the modified version uses your existing database and settings
# It also builds the frontend if needed

echo "🚀 Starting Modified OpenWebUI with Token Usage Tracking"
echo "============================================================"

# Determine the correct base directory (works on both Mac and Ubuntu)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Build frontend if build directory doesn't exist or if src files are newer
if [ ! -d "build" ] || [ "src" -nt "build" ]; then
    echo "📦 Building frontend (first time or source files changed)..."

    # Check if node_modules exists, if not run npm install
    if [ ! -d "node_modules" ]; then
        echo "📥 Installing npm dependencies..."
        npm install --legacy-peer-deps
    fi

    # Build the frontend
    echo "🔨 Building frontend with Vite..."
    npm run build

    if [ $? -ne 0 ]; then
        echo "❌ Frontend build failed! Please check the errors above."
        exit 1
    fi

    echo "✅ Frontend build completed successfully!"
else
    echo "✅ Frontend build is up to date (skipping build)"
fi

# Set up environment to use existing OpenWebUI data (Ubuntu-specific paths)
if [ -d "/home/tennisbowling" ]; then
    export DATA_DIR="/home/tennisbowling/.local/lib/python3.12/site-packages/open_webui/data"
    export PYTHONPATH="/home/tennisbowling/open-webui/backend"
    cd /home/tennisbowling/open-webui/backend
else
    # Development mode (Mac)
    export PYTHONPATH="$SCRIPT_DIR/backend"
    cd "$SCRIPT_DIR/backend"
fi

# Activate virtual environment
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Start the server
echo ""
echo "============================================================"
echo "📊 Starting server with enhanced features..."
echo "🔗 Web Interface will be available at: http://localhost:8081/"
echo ""
echo "✨ New Features:"
echo "   • Token Usage Display: Shows live IN/OUT/TOTAL stats above chat input"
echo "   • Reasoning Effort: Dropdown with Low/Medium/High options"
echo "   • Token Groups API: Create groups via /api/usage/groups endpoints"
echo "   • Title Generation Control: Admin can override and set model"
echo "   • Fixed Real-Time Streaming: Events now display in real-time"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8081