#!/bin/bash

# Fast development startup script for Open WebUI

echo "🚀 Starting Open WebUI Development Environment (Fast Mode)"

# Ensure we're using the right Node version
if command -v nvm &> /dev/null; then
    nvm use 22 > /dev/null 2>&1
fi

# Start frontend in fast mode (skip pyodide setup)
echo "📱 Starting frontend (fast mode - no pyodide)..."
npm run dev:fast &

# Wait a moment for frontend to start
sleep 3

# Start backend
echo "🔧 Starting backend..."
cd backend && uv run bash dev.sh &

echo ""
echo "✅ Development servers starting..."
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend:  http://localhost:8080"
echo "📚 API Docs: http://localhost:8080/docs"
echo ""
echo "💡 Note: Running in fast mode (pyodide disabled)"
echo "   Run 'npm run dev' if you need Python notebook features"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for interrupt
wait 