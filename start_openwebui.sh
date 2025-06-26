#!/bin/bash

# Start Open WebUI with MCP integration
echo "Starting Open WebUI with MCP integration..."

# Check if MCP proxies are running
if ! pgrep -f "mcpo.*8001" > /dev/null; then
    echo "Starting MCP proxies first..."
    ./start_mcp_proxies.sh
    echo "Waiting for MCP proxies to stabilize..."
    sleep 10
else
    echo "MCP proxies already running"
fi

# Start the frontend development server
echo "Starting frontend development server..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

# Start the backend server
echo "Starting backend server..."
cd backend
uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

echo ""
echo "🚀 Open WebUI is starting up!"
echo ""
echo "Frontend: http://localhost:5173"
echo "Backend API: http://localhost:8080"
echo ""
echo "MCP Proxy Endpoints:"
echo "  - Filesystem: http://localhost:8001/docs"
echo "  - Memory: http://localhost:8002/docs" 
echo "  - Browser: http://localhost:8003/docs"
echo ""
echo "Process IDs:"
echo "  Frontend: $FRONTEND_PID"
echo "  Backend: $BACKEND_PID"
echo ""
echo "To stop everything:"
echo "  pkill -f 'npm run dev'"
echo "  pkill -f 'uvicorn'"
echo "  pkill -f mcpo"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user to stop
wait