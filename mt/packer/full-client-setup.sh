#!/bin/bash
# Complete automated client setup - Droplet creation + Open WebUI deployment
# Usage: ./full-client-setup.sh CLIENT_NAME DOMAIN [SIZE] [REGION]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check dependencies
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}❌ doctl is not installed. Install with: brew install doctl${NC}"
    exit 1
fi

if [ $# -lt 2 ]; then
    echo "Usage: $0 CLIENT_NAME DOMAIN [SIZE] [REGION]"
    echo
    echo "Examples:"
    echo "  $0 acme-corp chat.acme.com"
    echo "  $0 beta-client beta.example.com s-4vcpu-8gb sfo3"
    echo
    echo "This will:"
    echo "  1. Create a new droplet from the golden image"
    echo "  2. Wait for it to boot"
    echo "  3. Deploy Open WebUI container for the client"
    echo "  4. Configure nginx (you'll still need to setup SSL manually)"
    exit 1
fi

CLIENT_NAME="$1"
DOMAIN="$2"
SIZE="${3:-s-2vcpu-4gb}"
REGION="${4:-nyc3}"

DROPLET_NAME="webui-${CLIENT_NAME}"
IMAGE_PATTERN="open-webui-multitenant"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Automated Client Setup                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo "Client:       ${CLIENT_NAME}"
echo "Domain:       ${DOMAIN}"
echo "Droplet Name: ${DROPLET_NAME}"
echo "Size:         ${SIZE}"
echo "Region:       ${REGION}"
echo

# Find latest golden image
echo -e "${BLUE}Finding golden image...${NC}"
IMAGE_ID=$(doctl compute image list --public=false --no-header --format ID,Name | \
    grep "$IMAGE_PATTERN" | \
    head -n 1 | \
    awk '{print $1}')

if [ -z "$IMAGE_ID" ]; then
    echo -e "${RED}❌ No golden image found matching: $IMAGE_PATTERN${NC}"
    echo
    echo "Run './build.sh' first to create the golden image"
    exit 1
fi

IMAGE_NAME=$(doctl compute image get "$IMAGE_ID" --format Name --no-header)
echo -e "${GREEN}✓${NC} Using image: $IMAGE_NAME"
echo

# Get SSH keys (use all available)
echo -e "${BLUE}Getting SSH keys...${NC}"
SSH_KEYS=$(doctl compute ssh-key list --format ID --no-header | tr '\n' ',' | sed 's/,$//')

if [ -z "$SSH_KEYS" ]; then
    echo -e "${RED}❌ No SSH keys found in your Digital Ocean account${NC}"
    echo "Add an SSH key first: doctl compute ssh-key import"
    exit 1
fi

echo -e "${GREEN}✓${NC} Using SSH keys: $SSH_KEYS"
echo

# Confirmation
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Ready to create droplet and deploy Open WebUI${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo
read -p "Continue? (Y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Step 1: Create droplet
echo
echo -e "${BLUE}[1/4] Creating droplet...${NC}"

DROPLET_OUTPUT=$(doctl compute droplet create "$DROPLET_NAME" \
    --image "$IMAGE_ID" \
    --size "$SIZE" \
    --region "$REGION" \
    --ssh-keys "$SSH_KEYS" \
    --tag-name "openwebui" \
    --tag-name "client-${CLIENT_NAME}" \
    --enable-monitoring \
    --enable-ipv6 \
    --wait \
    --format ID,Name,PublicIPv4 \
    --no-header)

if [ -z "$DROPLET_OUTPUT" ]; then
    echo -e "${RED}❌ Failed to create droplet${NC}"
    exit 1
fi

DROPLET_ID=$(echo "$DROPLET_OUTPUT" | awk '{print $1}')
DROPLET_IP=$(echo "$DROPLET_OUTPUT" | awk '{print $3}')

echo -e "${GREEN}✓${NC} Droplet created: $DROPLET_NAME ($DROPLET_IP)"

# Step 2: Wait for SSH
echo
echo -e "${BLUE}[2/4] Waiting for SSH to be ready...${NC}"

SSH_READY=false
for i in {1..60}; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 qbmgr@${DROPLET_IP} "echo 'Ready'" 2>/dev/null | grep -q "Ready"; then
        SSH_READY=true
        break
    fi
    echo -n "."
    sleep 5
done

echo

if [ "$SSH_READY" = false ]; then
    echo -e "${RED}❌ SSH not ready after 5 minutes${NC}"
    echo "Droplet created but SSH timeout. Try connecting manually:"
    echo "  ssh qbmgr@${DROPLET_IP}"
    exit 1
fi

echo -e "${GREEN}✓${NC} SSH is ready"

# Step 3: Deploy Open WebUI container
echo
echo -e "${BLUE}[3/4] Deploying Open WebUI container...${NC}"

DEPLOY_CMD="cd ~/open-webui/mt && ./start-template.sh \"${CLIENT_NAME}\" \"${DOMAIN}\""

if ssh -o StrictHostKeyChecking=no qbmgr@${DROPLET_IP} "$DEPLOY_CMD"; then
    echo -e "${GREEN}✓${NC} Container deployed successfully"
else
    echo -e "${RED}❌ Container deployment failed${NC}"
    echo "Droplet is running at: ${DROPLET_IP}"
    echo "SSH manually to debug: ssh qbmgr@${DROPLET_IP}"
    exit 1
fi

# Step 4: Save deployment info
echo
echo -e "${BLUE}[4/4] Saving deployment info...${NC}"

mkdir -p deployments

cat > "deployments/${CLIENT_NAME}.txt" <<EOF
Client: ${CLIENT_NAME}
Domain: ${DOMAIN}
Droplet Name: ${DROPLET_NAME}
Droplet ID: ${DROPLET_ID}
IP Address: ${DROPLET_IP}
Image: ${IMAGE_NAME}
Size: ${SIZE}
Region: ${REGION}
Created: $(date)

SSH Access:
  ssh qbmgr@${DROPLET_IP}

Container Name:
  openwebui-${DOMAIN//./-}

Next Steps:
  1. Point DNS: ${DOMAIN} -> ${DROPLET_IP}
  2. Setup SSL: ssh qbmgr@${DROPLET_IP} 'cd ~/open-webui/mt && ./client-manager.sh'
     Then select 'Setup SSL Certificate'
EOF

echo -e "${GREEN}✓${NC} Info saved to: deployments/${CLIENT_NAME}.txt"

# Final summary
echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║              ${GREEN}✅ CLIENT SETUP COMPLETE!${BLUE}                    ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}Droplet Information:${NC}"
echo "  Name:      ${DROPLET_NAME}"
echo "  IP:        ${DROPLET_IP}"
echo "  Domain:    ${DOMAIN}"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Point DNS A record:"
echo "     ${DOMAIN} → ${DROPLET_IP}"
echo
echo "  2. Setup SSL certificate (after DNS propagates):"
echo "     ${GREEN}ssh qbmgr@${DROPLET_IP}${NC}"
echo "     ${GREEN}cd ~/open-webui/mt && ./client-manager.sh${NC}"
echo "     Select: 'Setup SSL Certificate' → Enter domain: ${DOMAIN}"
echo
echo "  3. Access Open WebUI:"
echo "     https://${DOMAIN} (after SSL setup)"
echo
echo -e "${GREEN}✓${NC} Deployment info saved to: deployments/${CLIENT_NAME}.txt"
echo
