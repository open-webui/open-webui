#!/bin/bash

# QuantaBase Open WebUI Management Script

show_help() {
    echo "QuantaBase Open WebUI Management Commands"
    echo "========================================"
    echo
    echo "Container Management:"
    echo "  ./start.sh              - Start QuantaBase container"
    echo "  ./start.sh help         - Show this help"
    echo
    echo "Docker Commands:"
    echo "  docker stop open-webui-prod           - Stop the container"
    echo "  docker start open-webui-prod          - Start existing container"
    echo "  docker restart open-webui-prod        - Restart the container"
    echo "  docker logs -f open-webui-prod        - View live logs"
    echo "  docker logs open-webui-prod --tail 50 - View last 50 log lines"
    echo "  docker ps                              - List running containers"
    echo "  docker ps -a                           - List all containers"
    echo
    echo "Container Cleanup:"
    echo "  docker stop open-webui-prod && docker rm open-webui-prod"
    echo "                                         - Stop and remove container"
    echo "  docker system prune                    - Clean up unused Docker resources"
    echo
    echo "Access:"
    echo "  Local:      http://localhost:8080"
    echo "  Production: https://your-domain.com"
    echo
}

if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^open-webui-prod$"; then
    echo "Container 'open-webui-prod' already exists!"
    echo "Use: docker start open-webui-prod  (to start existing)"
    echo "Or:  docker stop open-webui-prod && docker rm open-webui-prod  (to remove first)"
    echo
    echo "Run './start.sh help' for more commands"
    exit 1
fi

echo "Starting QuantaBase Open WebUI..."

docker run -d \
    --name open-webui-prod \
    -p 8080:8080 \
    -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
    -e GOOGLE_CLIENT_SECRET=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 \
    -e GOOGLE_REDIRECT_URI=https://your-domain.com/oauth/google/callback \
    -e ENABLE_OAUTH_SIGNUP=true \
    -e OAUTH_ALLOWED_DOMAINS=martins.net \
    -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
    -e WEBUI_NAME="QuantaBase" \
    -e USER_PERMISSIONS_CHAT_CONTROLS=false \
    -v open-webui-data:/app/backend/data \
    --restart unless-stopped \
    ghcr.io/imagicrafter/open-webui:main

if [ $? -eq 0 ]; then
    echo "✅ QuantaBase Open WebUI started successfully!"
    echo "📱 Access at: http://localhost:8080"
    echo "📋 Run './start.sh help' for management commands"
else
    echo "❌ Failed to start container"
    exit 1
fi