#!/bin/bash

# Start MCP proxies for Open WebUI integration
# This script starts multiple MCP servers as OpenAPI proxies

echo "Starting MCP proxy servers for Open WebUI integration..."

# Kill any existing mcpo processes
pkill -f mcpo

# Wait a moment for cleanup
sleep 2

# Start filesystem MCP proxy on port 8001
echo "Starting filesystem MCP proxy on port 8001..."
mcpo --port 8001 --api-key "openwebui-filesystem" -- npx -y @modelcontextprotocol/server-filesystem /Users/gwyn &
FILESYSTEM_PID=$!

# Start openmemory MCP proxy on port 8002
echo "Starting openmemory MCP proxy on port 8002..."
OPENMEMORY_API_KEY="om-tbgchfv962np1xm0alzu5mzsirwa0tky" \
CLIENT_NAME="claude" \
mcpo --port 8002 --api-key "openwebui-memory" -- npx -y openmemory &
MEMORY_PID=$!

# Start puppeteer MCP proxy on port 8003
echo "Starting puppeteer MCP proxy on port 8003..."
mcpo --port 8003 --api-key "openwebui-browser" -- npx -y @modelcontextprotocol/server-puppeteer &
PUPPETEER_PID=$!

# Wait for servers to start
echo "Waiting for servers to initialize..."
sleep 5

# Test the endpoints
echo "Testing MCP proxy endpoints..."
echo "Filesystem proxy: http://localhost:8001/docs"
echo "Memory proxy: http://localhost:8002/docs" 
echo "Browser proxy: http://localhost:8003/docs"

# Check if servers are running
if curl -s -H "Authorization: Bearer openwebui-filesystem" http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Filesystem MCP proxy is running"
else
    echo "❌ Filesystem MCP proxy failed to start"
fi

if curl -s -H "Authorization: Bearer openwebui-memory" http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Memory MCP proxy is running"
else
    echo "❌ Memory MCP proxy failed to start"
fi

if curl -s -H "Authorization: Bearer openwebui-browser" http://localhost:8003/health > /dev/null 2>&1; then
    echo "✅ Browser MCP proxy is running"
else
    echo "❌ Browser MCP proxy failed to start"
fi

echo ""
echo "MCP Proxy servers started!"
echo "Process IDs:"
echo "  Filesystem: $FILESYSTEM_PID"
echo "  Memory: $MEMORY_PID"
echo "  Browser: $PUPPETEER_PID"
echo ""
echo "To stop all MCP proxies, run: pkill -f mcpo"
echo ""
echo "Configure these endpoints in Open WebUI:"
echo "  - http://localhost:8001 (filesystem tools)"
echo "  - http://localhost:8002 (memory management)"
echo "  - http://localhost:8003 (browser automation)"