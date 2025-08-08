#!/bin/bash

# Start Modified OpenWebUI with Token Usage Tracking and Reasoning Effort
# This script ensures the modified version uses your existing database and settings

echo "🚀 Starting Modified OpenWebUI with Token Usage Tracking"
echo "=" * 60

# Set up environment to use existing OpenWebUI data
export DATA_DIR="/home/tennisbowling/.local/lib/python3.12/site-packages/open_webui/data"
export PYTHONPATH="/home/tennisbowling/open-webui/backend"

# Change to the correct directory
cd /home/tennisbowling/open-webui/backend

# Activate virtual environment
source ../venv/bin/activate

# Start the server
echo "📊 Starting server with token usage tracking and reasoning effort features..."
echo "🔗 Web Interface will be available at: http://localhost:8081/"
echo ""
echo "✨ New Features:"
echo "   • Token Usage Display: Shows live IN/OUT/TOTAL stats above chat input"
echo "   • Reasoning Effort: Dropdown with Low/Medium/High options"
echo "   • Token Groups API: Create groups via /api/usage/groups endpoints"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8081