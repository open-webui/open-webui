#!/bin/bash
# AI UI - Deployment Script
# Run this script on the Hetzner server to deploy or update AI UI

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.prod.yaml"
BRANCH="testy"

echo -e "${GREEN}=== AI UI Deployment ===${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: $COMPOSE_FILE not found"
    echo "Make sure you're in the ai_ui repository root"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Copy .env.production.example to .env and configure it"
    echo "  cp .env.production.example .env"
    echo "  nano .env"
    exit 1
fi

echo -e "${YELLOW}Step 1/3: Pulling latest changes...${NC}"
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

echo -e "${YELLOW}Step 2/3: Pulling latest Docker images...${NC}"
docker compose -f $COMPOSE_FILE pull

echo -e "${YELLOW}Step 3/3: Restarting services...${NC}"
docker compose -f $COMPOSE_FILE up -d

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
docker compose -f $COMPOSE_FILE ps
echo ""
echo "AI UI is available at: http://$(hostname -I | awk '{print $1}'):3100"
