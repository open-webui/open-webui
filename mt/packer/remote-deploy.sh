#!/bin/bash
# Deploy Open WebUI clients remotely on a droplet
# Usage: ./remote-deploy.sh CLIENT_NAME DROPLET_IP [DOMAIN] [PORT]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ $# -lt 2 ]; then
    echo "Usage: $0 CLIENT_NAME DROPLET_IP [DOMAIN] [PORT]"
    echo
    echo "Examples:"
    echo "  $0 acme-corp 159.203.94.143"
    echo "  $0 acme-corp 159.203.94.143 chat.acme.com"
    echo "  $0 acme-corp 159.203.94.143 chat.acme.com 8081"
    exit 1
fi

CLIENT_NAME="$1"
DROPLET_IP="$2"
DOMAIN="${3:-}"
PORT="${4:-}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Remote Client Deployment                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

echo "Client:  ${CLIENT_NAME}"
echo "Droplet: ${DROPLET_IP}"
[ -n "$DOMAIN" ] && echo "Domain:  ${DOMAIN}"
[ -n "$PORT" ] && echo "Port:    ${PORT}"
echo

# Test SSH connectivity
echo -e "${BLUE}Testing SSH connection...${NC}"
if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 qbmgr@${DROPLET_IP} "echo 'Connected'" &>/dev/null; then
    echo -e "${RED}❌ Cannot connect via SSH to qbmgr@${DROPLET_IP}${NC}"
    echo
    echo "Possible issues:"
    echo "  - SSH keys not added to droplet"
    echo "  - Droplet not fully booted yet"
    echo "  - Network connectivity issue"
    exit 1
fi
echo -e "${GREEN}✓${NC} SSH connection successful"
echo

# Build deployment command
DEPLOY_CMD="cd ~/open-webui/mt && "

if [ -n "$DOMAIN" ] && [ -n "$PORT" ]; then
    # Non-interactive deployment with all parameters
    DEPLOY_CMD+="./start-template.sh \"${CLIENT_NAME}\" \"${DOMAIN}\" ${PORT}"
elif [ -n "$DOMAIN" ]; then
    # With domain, auto-assign port
    DEPLOY_CMD+="./start-template.sh \"${CLIENT_NAME}\" \"${DOMAIN}\""
else
    # Interactive mode
    DEPLOY_CMD+="./client-manager.sh"
fi

echo -e "${BLUE}Executing deployment on remote droplet...${NC}"
echo -e "${YELLOW}Command: ${DEPLOY_CMD}${NC}"
echo

# Execute deployment remotely
ssh -o StrictHostKeyChecking=no qbmgr@${DROPLET_IP} "$DEPLOY_CMD"

DEPLOY_EXIT_CODE=$?

echo
if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"

    if [ -n "$DOMAIN" ]; then
        echo
        echo "Next steps:"
        echo "1. Point DNS record for ${DOMAIN} to ${DROPLET_IP}"
        echo "2. Run SSL setup:"
        echo "   ${YELLOW}ssh qbmgr@${DROPLET_IP} 'cd ~/open-webui/mt && ./client-manager.sh'${NC}"
        echo "   Then select 'Setup SSL Certificate'"
    fi
else
    echo -e "${RED}❌ Deployment failed with exit code: ${DEPLOY_EXIT_CODE}${NC}"
    exit $DEPLOY_EXIT_CODE
fi
