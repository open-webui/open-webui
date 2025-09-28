#!/bin/bash

# Multi-Client Open WebUI Template Script
# Usage: ./start-template.sh CLIENT_NAME PORT [DOMAIN]
# If DOMAIN is not provided, auto-detects environment

if [ $# -lt 2 ]; then
    echo "Usage: $0 CLIENT_NAME PORT [DOMAIN]"
    echo "Examples:"
    echo "  $0 acme-corp 8081                    # Auto-detect environment"
    echo "  $0 acme-corp 8081 acme.example.com   # Force production domain"
    exit 1
fi

CLIENT_NAME=$1
PORT=$2
DOMAIN=$3
CONTAINER_NAME="openwebui-${CLIENT_NAME}"
VOLUME_NAME="openwebui-${CLIENT_NAME}-data"

# Auto-detect environment if domain not provided
if [ -z "$DOMAIN" ]; then
    # Check if we're in a production environment
    if [ -f "/etc/hostname" ] && grep -q "droplet\|server\|prod" /etc/hostname 2>/dev/null; then
        # Production environment - use production domain
        DOMAIN="${CLIENT_NAME}.yourdomain.com"
        REDIRECT_URI="https://${DOMAIN}/oauth/google/callback"
        ENVIRONMENT="production"
    else
        # Development environment - use localhost
        DOMAIN="localhost:${PORT}"
        REDIRECT_URI="http://127.0.0.1:${PORT}/oauth/google/callback"
        ENVIRONMENT="development"
        # Check if nginx proxy is running on port 80
        if netstat -ln 2>/dev/null | grep -q ":80 " || lsof -i :80 >/dev/null 2>&1; then
            echo "Detected nginx proxy on port 80 - configuring for proxy mode"
            REDIRECT_URI="http://localhost/oauth/google/callback"
            BASE_URL="http://localhost"
        fi
    fi
else
    # Domain explicitly provided
    if [[ "$DOMAIN" == localhost* ]] || [[ "$DOMAIN" == 127.0.0.1* ]]; then
        REDIRECT_URI="http://${DOMAIN}/oauth/google/callback"
        ENVIRONMENT="development"
    else
        REDIRECT_URI="https://${DOMAIN}/oauth/google/callback"
        ENVIRONMENT="production"
    fi
fi

echo "Starting Open WebUI for client: ${CLIENT_NAME}"
echo "Container: ${CONTAINER_NAME}"
echo "Port: ${PORT}"
echo "Domain: ${DOMAIN}"
echo "Environment: ${ENVIRONMENT}"
echo "Redirect URI: ${REDIRECT_URI}"

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '${CONTAINER_NAME}' already exists!"
    echo "Use: docker start ${CONTAINER_NAME}"
    exit 1
fi

docker_cmd="docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:8080 \
    -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
    -e GOOGLE_CLIENT_SECRET=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 \
    -e GOOGLE_REDIRECT_URI=${REDIRECT_URI} \
    -e ENABLE_OAUTH_SIGNUP=true \
    -e OAUTH_ALLOWED_DOMAINS=martins.net \
    -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
    -e WEBUI_NAME=\"QuantaBase - ${CLIENT_NAME}\" \
    -e USER_PERMISSIONS_CHAT_CONTROLS=false"

# Add BASE_URL if set (for nginx proxy mode)
if [[ -n "$BASE_URL" ]]; then
    docker_cmd="$docker_cmd -e WEBUI_BASE_URL=${BASE_URL}"
fi

docker_cmd="$docker_cmd \
    -v ${VOLUME_NAME}:/app/backend/data \
    --restart unless-stopped \
    ghcr.io/imagicrafter/open-webui:main"

eval $docker_cmd

if [ $? -eq 0 ]; then
    echo "✅ ${CLIENT_NAME} Open WebUI started successfully!"
    echo "📱 Internal: http://localhost:${PORT}"
    echo "🌐 External: https://${DOMAIN}"
    echo "📦 Volume: ${VOLUME_NAME}"
else
    echo "❌ Failed to start container for ${CLIENT_NAME}"
    exit 1
fi