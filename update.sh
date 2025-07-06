#!/bin/bash
# Quick update script for custom Open WebUI

set -e

echo "🔄 Updating Open WebUI Custom Build..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Pull latest base image
echo -e "${YELLOW}📥 Pulling latest Open WebUI...${NC}"
docker pull ghcr.io/open-webui/open-webui:latest

# 2. Create backup of current image
echo -e "${YELLOW}💾 Creating backup...${NC}"
docker tag xynthorai-open-webui:xynthor xynthorai-open-webui:backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true

# 3. Rebuild custom image
echo -e "${YELLOW}🔨 Building custom image...${NC}"
cd "$(dirname "$0")"
docker build -f Dockerfile.local-assets -t xynthorai-open-webui:xynthor . --no-cache

# 4. Show version info
echo -e "${GREEN}✅ Build complete!${NC}"
echo "Image details:"
docker images xynthorai-open-webui:xynthor --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"

# 5. Reminder to restart
echo -e "${YELLOW}📌 To apply update, run:${NC}"
echo "cd /Users/admin_pro/_Web/xynthorai-system"
echo "docker-compose restart open-webui"