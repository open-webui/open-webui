#!/bin/bash

case "$1" in
    "restart"|"r")
        echo "🔄 Restarting containers..."
        ./stop.sh --hard
        echo ""
        ./start.sh
        ;;
    "logs"|"l")
        echo "📋 Showing container logs (Ctrl+C to exit)..."
        echo ""
        docker compose -f docker-compose.custom.yml logs -f
        ;;
    "status"|"s")
        echo "📊 Container status:"
        echo ""
        docker compose -f docker-compose.custom.yml ps
        ;;
    "models"|"m")
        echo "🤖 Available Ollama models:"
        echo ""
        docker compose -f docker-compose.custom.yml exec ollama ollama list
        ;;
    "pull"|"p")
        if [[ -z "$2" ]]; then
            echo "❌ Please specify a model to download"
            echo "💡 Example: ./manage.sh pull llama2"
            echo "💡 Popular models: llama2, llama3.2, mistral, codellama"
        else
            echo "⬇️  Downloading model: $2"
            docker compose -f docker-compose.custom.yml exec ollama ollama pull "$2"
        fi
        ;;
    "pipelines"|"pipes")
        echo "🔧 Available Pipelines:"
        echo ""
        curl -s -H "Authorization: Bearer 0p3n-w3bu!" http://localhost:9099/models | jq . 2>/dev/null || echo "❌ Pipelines not running or jq not installed"
        ;;
    "test-pipeline"|"tp")
        echo "🧪 Testing pipeline connection..."
        echo ""
        response=$(curl -s \
                   -H "Authorization: Bearer 0p3n-w3bu!" \
                   -H "Content-Type: application/json" \
                   -d '{
                     "model": "test",
                     "messages": [{"role": "user", "content": "Hello pipeline!"}],
                     "stream": false
                   }' \
                   -w "HTTP_CODE:%{http_code}" \
                   http://localhost:9099/v1/chat/completions)
        
        http_code=$(echo "$response" | grep -o "HTTP_CODE:[0-9]*" | cut -d':' -f2)
        body=$(echo "$response" | sed 's/HTTP_CODE:[0-9]*$//')
        
        if [ "$http_code" = "200" ]; then
            echo "✅ Pipeline connection successful!"
            echo "Response: $body"
        else
            echo "❌ Pipeline connection failed (HTTP $http_code)"
            echo "Response: $body"
            echo ""
            echo "💡 Try: curl -s http://localhost:9099/ to check if pipelines is running"
        fi
        ;;
    "install-pipeline"|"ip")
        if [[ -z "$2" ]]; then
            echo "❌ Please specify a pipeline URL to install"
            echo "💡 Example: ./manage.sh install-pipeline https://github.com/open-webui/pipelines/blob/main/examples/filters/function_calling_filter_pipeline.py"
        else
            echo "📦 Installing pipeline from: $2"
            echo ""
            response=$(curl -s \
                       -H "Authorization: Bearer 0p3n-w3bu!" \
                       -H "Content-Type: application/json" \
                       -d "{\"url\": \"$2\"}" \
                       -w "HTTP_CODE:%{http_code}" \
                       http://localhost:9099/admin/pipelines/install)
            
            http_code=$(echo "$response" | grep -o "HTTP_CODE:[0-9]*" | cut -d':' -f2)
            body=$(echo "$response" | sed 's/HTTP_CODE:[0-9]*$//')
            
            if [ "$http_code" = "200" ]; then
                echo "✅ Pipeline installed successfully!"
                echo "Response: $body"
            else
                echo "❌ Pipeline installation failed (HTTP $http_code)"
                echo "Response: $body"
                echo ""
                echo "💡 Note: Some pipelines need to be installed via PIPELINES_URLS environment variable"
                echo "💡 Try restarting containers: ./manage.sh restart"
            fi
        fi
        ;;
    "pipeline-logs"|"pl")
        echo "📋 Pipeline container logs (Ctrl+C to exit)..."
        echo ""
        docker compose -f docker-compose.custom.yml logs -f pipelines
        ;;
    "shell"|"sh")
        if [[ -z "$2" ]]; then
            echo "🐚 Opening shell in Open WebUI container..."
            docker compose -f docker-compose.custom.yml exec open-webui bash
        else
            echo "🐚 Opening shell in $2 container..."
            docker compose -f docker-compose.custom.yml exec "$2" bash
        fi
        ;;
    *)
        echo "🛠️  Open WebUI Management Script"
        echo ""
        echo "Usage: ./manage.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  restart, r              - Restart all containers"
        echo "  logs, l                 - View live logs"
        echo "  status, s               - Show container status"
        echo "  models, m               - List downloaded Ollama models"
        echo "  pull, p [model]         - Download an Ollama model"
        echo "  pipelines, pipes        - List available pipelines"
        echo "  test-pipeline, tp       - Test pipeline connection"
        echo "  install-pipeline, ip    - Install a pipeline from URL"
        echo "  pipeline-logs, pl       - View pipeline container logs"
        echo "  shell, sh [service]     - Open shell in container (default: open-webui)"
        echo ""
        echo "Examples:"
        echo "  ./manage.sh restart"
        echo "  ./manage.sh logs"
        echo "  ./manage.sh pull llama2"
        echo "  ./manage.sh test-pipeline"
        echo "  ./manage.sh install-pipeline https://github.com/open-webui/pipelines/blob/main/examples/filters/function_calling_filter_pipeline.py"
        echo "  ./manage.sh shell ollama"
        echo ""
        ;;
esac
