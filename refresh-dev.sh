#!/bin/bash

# mAI Development Server Refresher
# This script refreshes both frontend and backend servers to see changes

echo "🔄 Refreshing mAI Development Servers..."
echo "================================================"

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "backend" ]; then
    echo "❌ Error: Please run this script from the mAI project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Function to check if a process is running
check_process() {
    if pgrep -f "$1" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Stop existing servers
echo "🛑 Stopping existing servers..."

# Stop frontend (npm run dev)
if check_process "npm run dev"; then
    echo "  • Stopping Frontend..."
    pkill -f "npm run dev"
    sleep 2
fi

# Stop backend (uvicorn)
if check_process "uvicorn.*open_webui"; then
    echo "  • Stopping Backend..."
    pkill -f "uvicorn.*open_webui"
    sleep 2
fi

# Stop any remaining dev.sh processes
if check_process "dev.sh"; then
    echo "  • Stopping dev.sh..."
    pkill -f "dev.sh"
    sleep 2
fi

echo "✅ Servers stopped"
echo ""

# Wait a moment for clean shutdown
sleep 2

# Function to cleanup on exit
cleanup() {
    echo -e "\n🛑 Stopping servers..."
    kill 0
}
trap cleanup EXIT

# Start backend in background
echo "🔧 Restarting Backend Server..."
cd backend
source .venv/bin/activate
sh dev.sh &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 3

# Start frontend in background
echo "🎨 Restarting Frontend Server..."
npm run dev &
FRONTEND_PID=$!

# Wait for servers to start
echo "⏳ Waiting for servers to start..."
sleep 5

echo ""
echo "✅ Development servers refreshed successfully!"
echo "================================================"
echo "🔧 Backend API: http://localhost:8080"
echo "🔧 API Docs: http://localhost:8080/docs"
echo "🎨 Frontend: http://localhost:5173"
echo "================================================"
echo ""
echo "💡 Don't forget to hard refresh your browser: Ctrl+Shift+R (or Cmd+Shift+R)"
echo "🛑 Press Ctrl+C to stop both servers"
echo ""

# Keep script running and show logs
wait