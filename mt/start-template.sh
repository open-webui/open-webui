#!/bin/bash

# Multi-Client Open WebUI Template Script
# Usage: ./start-template.sh CLIENT_NAME PORT DOMAIN CONTAINER_NAME FQDN
# FQDN-based container naming for multi-tenant deployments

if [ $# -lt 5 ]; then
    echo "Usage: $0 CLIENT_NAME PORT DOMAIN CONTAINER_NAME FQDN"
    echo "Examples:"
    echo "  $0 chat 8081 chat.client-a.com openwebui-chat-client-a-com chat.client-a.com"
    echo "  $0 chat 8082 localhost:8082 openwebui-localhost-8082 localhost:8082"
    exit 1
fi

CLIENT_NAME=$1
PORT=$2
DOMAIN=$3
CONTAINER_NAME=$4
FQDN=$5
VOLUME_NAME="${CONTAINER_NAME}-data"

# Set redirect URI and environment based on domain type
if [[ "$DOMAIN" == localhost* ]] || [[ "$DOMAIN" == 127.0.0.1* ]]; then
    REDIRECT_URI="http://${DOMAIN}/oauth/google/callback"
    ENVIRONMENT="development"
else
    REDIRECT_URI="https://${DOMAIN}/oauth/google/callback"
    ENVIRONMENT="production"
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
    -e USER_PERMISSIONS_CHAT_CONTROLS=false \
    -e FQDN=\"${FQDN}\" \
    -e CLIENT_NAME=\"${CLIENT_NAME}\""

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