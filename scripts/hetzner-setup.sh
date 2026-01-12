#!/bin/bash
# AI UI - Hetzner Cloud Infrastructure Setup
# This script provisions a Hetzner Cloud server with Docker for AI UI deployment

set -e

# Configuration
SERVER_NAME="ai-ui-dev"
FIREWALL_NAME="ai-ui-firewall"
SSH_KEY_NAME="ai-ui-key"
SERVER_TYPE="cx22"  # 2 vCPU, 4GB RAM, €3.49/month
LOCATION="nbg1"     # Nuremberg, Germany (cheapest)
IMAGE="docker-ce"   # Ubuntu with Docker pre-installed

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AI UI Hetzner Setup ===${NC}"
echo ""

# Check if hcloud is installed
if ! command -v hcloud &> /dev/null; then
    echo -e "${RED}Error: hcloud CLI is not installed${NC}"
    echo "Install with: brew install hcloud"
    exit 1
fi

# Check if context is configured
if ! hcloud context active &> /dev/null; then
    echo -e "${RED}Error: No hcloud context configured${NC}"
    echo "Run: hcloud context create ai-ui-deploy"
    echo "Then paste your Hetzner API token"
    exit 1
fi

echo -e "${YELLOW}Step 1/4: Setting up SSH key...${NC}"
if hcloud ssh-key describe $SSH_KEY_NAME &> /dev/null; then
    echo "  SSH key '$SSH_KEY_NAME' already exists"
else
    if [ -f ~/.ssh/id_rsa.pub ]; then
        hcloud ssh-key create --name $SSH_KEY_NAME --public-key-from-file ~/.ssh/id_rsa.pub
        echo "  SSH key created from ~/.ssh/id_rsa.pub"
    elif [ -f ~/.ssh/id_ed25519.pub ]; then
        hcloud ssh-key create --name $SSH_KEY_NAME --public-key-from-file ~/.ssh/id_ed25519.pub
        echo "  SSH key created from ~/.ssh/id_ed25519.pub"
    else
        echo -e "${RED}Error: No SSH public key found${NC}"
        echo "Generate one with: ssh-keygen -t ed25519"
        exit 1
    fi
fi

echo -e "${YELLOW}Step 2/4: Setting up firewall...${NC}"
if hcloud firewall describe $FIREWALL_NAME &> /dev/null; then
    echo "  Firewall '$FIREWALL_NAME' already exists"
else
    hcloud firewall create --name $FIREWALL_NAME
    echo "  Firewall created"
fi

# Add firewall rules (ignore errors if rules already exist)
echo "  Adding firewall rules..."
hcloud firewall add-rule $FIREWALL_NAME --direction in --protocol tcp --port 22 --source-ips 0.0.0.0/0 --source-ips ::/0 --description "SSH" 2>/dev/null || true
hcloud firewall add-rule $FIREWALL_NAME --direction in --protocol tcp --port 80 --source-ips 0.0.0.0/0 --source-ips ::/0 --description "HTTP" 2>/dev/null || true
hcloud firewall add-rule $FIREWALL_NAME --direction in --protocol tcp --port 443 --source-ips 0.0.0.0/0 --source-ips ::/0 --description "HTTPS" 2>/dev/null || true
hcloud firewall add-rule $FIREWALL_NAME --direction in --protocol tcp --port 3100 --source-ips 0.0.0.0/0 --source-ips ::/0 --description "AI-UI" 2>/dev/null || true
hcloud firewall add-rule $FIREWALL_NAME --direction in --protocol icmp --source-ips 0.0.0.0/0 --source-ips ::/0 --description "ICMP" 2>/dev/null || true
echo "  Firewall rules configured"

echo -e "${YELLOW}Step 3/4: Creating server...${NC}"
if hcloud server describe $SERVER_NAME &> /dev/null; then
    echo "  Server '$SERVER_NAME' already exists"
    SERVER_IP=$(hcloud server ip $SERVER_NAME)
else
    echo "  Creating $SERVER_TYPE server in $LOCATION..."
    hcloud server create \
        --name $SERVER_NAME \
        --type $SERVER_TYPE \
        --image $IMAGE \
        --location $LOCATION \
        --ssh-key $SSH_KEY_NAME \
        --firewall $FIREWALL_NAME

    # Wait a moment for the server to initialize
    sleep 5
    SERVER_IP=$(hcloud server ip $SERVER_NAME)
    echo "  Server created successfully!"
fi

echo -e "${YELLOW}Step 4/4: Server ready!${NC}"
echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Server IP: $SERVER_IP"
echo "Server Type: $SERVER_TYPE (2 vCPU, 4GB RAM)"
echo "Monthly Cost: ~€3.49 (~\$4 USD)"
echo ""
echo "Connect with:"
echo "  ssh root@$SERVER_IP"
echo ""
echo "Next steps:"
echo "  1. SSH into the server"
echo "  2. Clone your repository"
echo "  3. Run: docker compose -f docker-compose.prod.yaml up -d"
