#!/bin/bash

echo "Stopping all Open WebUI and MCP services..."

# Stop Open WebUI services
echo "Stopping Open WebUI frontend..."
pkill -f "npm run dev"

echo "Stopping Open WebUI backend..."
pkill -f "uvicorn.*open_webui"

# Stop MCP proxies
echo "Stopping MCP proxies..."
pkill -f mcpo

echo "Waiting for processes to terminate..."
sleep 3

echo "✅ All services stopped"