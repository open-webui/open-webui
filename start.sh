#!/bin/bash

echo "🚀 Starting Open WebUI, SearXNG, and Ollama containers..."
echo ""

# Start the containers
docker compose -f docker-compose.custom.yml up -d

echo ""
echo "✅ Containers started!"
echo ""
echo "📍 Access points:"
echo "   • Open WebUI:  http://localhost:3000"
echo "   • SearXNG:     http://localhost:8080" 
echo "   • Ollama API:  http://localhost:11434"
echo ""
echo "📝 To view logs: docker compose -f docker-compose.custom.yml logs -f"
echo "📝 To stop: ./stop.sh"
echo ""
echo "⚠️  If this is your first time:"
echo "   1. Wait a minute for containers to fully start"
echo "   2. Download models: docker compose -f docker-compose.custom.yml exec ollama ollama pull llama2"
echo "   3. Configure SearXNG in Open WebUI admin settings"
echo ""
