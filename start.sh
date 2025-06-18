#!/bin/bash

echo "🚀 Starting Open WebUI, SearXNG, Ollama, and Pipelines containers..."
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
echo "   • Pipelines:   http://localhost:9099"
echo ""
echo "📝 To view logs: docker compose -f docker-compose.custom.yml logs -f"
echo "📝 To stop: ./stop.sh"
echo ""
echo "⚠️  If this is your first time:"
echo "   1. Wait a minute for containers to fully start"
echo "   2. Download models: ./manage.sh pull llama2"
echo "   3. Configure SearXNG in Open WebUI admin settings"
echo "   4. Connect Pipelines: Set API URL to http://localhost:9099 with API key '0p3n-w3bu!'"
echo "   5. Test pipeline: ./manage.sh test-pipeline"
echo ""
