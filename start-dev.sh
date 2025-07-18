#!/bin/bash

# mAI Development Server Starter
# This script starts both frontend and backend servers for development

echo "🚀 Starting mAI Development Servers..."
echo "================================================"

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "backend" ]; then
    echo "❌ Error: Please run this script from the mAI project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if backend virtual environment exists
if [ ! -d "backend/.venv" ]; then
    echo "❌ Error: Backend virtual environment not found at backend/.venv"
    echo "Please create it first: cd backend && python -m venv .venv"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n🛑 Stopping servers..."
    kill 0
}
trap cleanup EXIT

# Start backend in background
echo "🔧 Starting Backend Server..."
cd backend
source .venv/bin/activate
sh dev.sh &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 3

# Start frontend in background
echo "🎨 Starting Frontend Server..."
npm run dev &
FRONTEND_PID=$!

# Wait for servers to start
echo "⏳ Waiting for servers to start..."
sleep 5

echo ""
echo "✅ Development servers started successfully!"
echo "================================================"
echo "🔧 Backend API: http://localhost:8080"
echo "🔧 API Docs: http://localhost:8080/docs"
echo "🎨 Frontend: http://localhost:5173"
echo "================================================"
echo ""
echo "📝 Use Firefox for testing (as recommended in project_info.md)"
echo "🛑 Press Ctrl+C to stop both servers"
echo ""

# Keep script running and show logs
wait