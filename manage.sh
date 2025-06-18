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
        echo "  restart, r          - Restart all containers"
        echo "  logs, l             - View live logs"
        echo "  status, s           - Show container status"
        echo "  models, m           - List downloaded Ollama models"
        echo "  pull, p [model]     - Download an Ollama model"
        echo "  shell, sh [service] - Open shell in container (default: open-webui)"
        echo ""
        echo "Examples:"
        echo "  ./manage.sh restart"
        echo "  ./manage.sh logs"
        echo "  ./manage.sh pull llama2"
        echo "  ./manage.sh shell ollama"
        echo ""
        ;;
esac
