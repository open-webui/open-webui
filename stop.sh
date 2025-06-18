#!/bin/bash

echo "🛑 Stopping Open WebUI, SearXNG, and Ollama containers..."
echo ""

# Check if user wants to remove volumes
if [[ "$1" == "--clean" || "$1" == "-c" ]]; then
    echo "🧹 Cleaning up containers AND removing all data (volumes)..."
    docker compose -f docker-compose.custom.yml down -v --remove-orphans
    echo "⚠️  All data has been removed (models, chats, etc.)"
elif [[ "$1" == "--hard" || "$1" == "-h" ]]; then
    echo "💥 Force stopping and removing containers..."
    docker compose -f docker-compose.custom.yml down --remove-orphans
    echo "✅ Containers stopped and removed"
else
    echo "⏹️  Stopping containers (keeping data)..."
    docker compose -f docker-compose.custom.yml stop
    echo "✅ Containers stopped (data preserved)"
fi

echo ""
echo "📝 Usage options:"
echo "   ./stop.sh           - Stop containers (keep data)"
echo "   ./stop.sh --hard    - Stop and remove containers"
echo "   ./stop.sh --clean   - Stop, remove containers AND delete all data"
echo ""
echo "🚀 To start again: ./start.sh"
echo ""
