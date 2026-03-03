#!/bin/bash
set -e
echo "🔄 Pulling latest changes..."
cd /opt/open-webui
git pull origin main
echo "🏗️ Building Docker image..."
docker compose -f docker-compose.prod.yml up -d --build
echo "🧹 Cleaning up old images..."
docker image prune -f
echo "✅ Deployment complete!"