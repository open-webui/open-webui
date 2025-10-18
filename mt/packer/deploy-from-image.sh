#!/bin/bash
# Deploy a droplet from the golden image
# Usage: ./deploy-from-image.sh CLIENT_NAME

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}❌ doctl is not installed${NC}"
    echo
    echo "Install doctl:"
    echo "  macOS:   brew install doctl"
    echo "  Linux:   snap install doctl"
    echo
    echo "Then authenticate:"
    echo "  doctl auth init"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Deploy Droplet from Golden Image                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Client name
if [ $# -ge 1 ]; then
    CLIENT_NAME="$1"
else
    read -p "Enter client name (e.g., acme-corp): " CLIENT_NAME
fi

DROPLET_NAME="webui-${CLIENT_NAME}"

# Configuration prompts with defaults
read -p "Droplet size (default: s-2vcpu-4gb): " SIZE
SIZE="${SIZE:-s-2vcpu-4gb}"

read -p "Region (default: nyc3): " REGION
REGION="${REGION:-nyc3}"

read -p "Image name pattern (default: open-webui-multitenant): " IMAGE_PATTERN
IMAGE_PATTERN="${IMAGE_PATTERN:-open-webui-multitenant}"

echo
echo -e "${BLUE}Finding latest golden image...${NC}"

# Get the latest custom image matching pattern
IMAGE_ID=$(doctl compute image list --public=false --no-header --format ID,Name,Slug | \
    grep "$IMAGE_PATTERN" | \
    head -n 1 | \
    awk '{print $1}')

if [ -z "$IMAGE_ID" ]; then
    echo -e "${RED}❌ No custom image found matching: $IMAGE_PATTERN${NC}"
    echo
    echo "Available custom images:"
    doctl compute image list --public=false --format Name,ID
    exit 1
fi

IMAGE_NAME=$(doctl compute image get "$IMAGE_ID" --format Name --no-header)
echo -e "${GREEN}✓${NC} Found image: $IMAGE_NAME (ID: $IMAGE_ID)"
echo

# Get SSH keys
echo -e "${BLUE}Available SSH keys:${NC}"
doctl compute ssh-key list --format Name,ID,Fingerprint

echo
read -p "Enter SSH key ID(s) (comma-separated, or 'all' for all keys): " SSH_KEYS

if [ "$SSH_KEYS" = "all" ]; then
    SSH_KEYS=$(doctl compute ssh-key list --format ID --no-header | tr '\n' ',' | sed 's/,$//')
fi

echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "Deployment Configuration:"
echo "  Client:       ${CLIENT_NAME}"
echo "  Droplet Name: ${DROPLET_NAME}"
echo "  Image:        ${IMAGE_NAME}"
echo "  Size:         ${SIZE}"
echo "  Region:       ${REGION}"
echo "  SSH Keys:     ${SSH_KEYS}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo

read -p "Create droplet? (Y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

echo
echo -e "${GREEN}Creating droplet...${NC}"

# Create droplet
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
    --format ID,Name,PublicIPv4,Status \
    --no-header)

if [ -z "$DROPLET_OUTPUT" ]; then
    echo -e "${RED}❌ Failed to create droplet${NC}"
    exit 1
fi

DROPLET_ID=$(echo "$DROPLET_OUTPUT" | awk '{print $1}')
DROPLET_IP=$(echo "$DROPLET_OUTPUT" | awk '{print $3}')

echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Droplet Created Successfully!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo
echo "Droplet Details:"
echo "  ID:        $DROPLET_ID"
echo "  Name:      $DROPLET_NAME"
echo "  IP:        $DROPLET_IP"
echo "  Status:    Active"
echo

# Save deployment info
DEPLOY_INFO_FILE="deployments/${CLIENT_NAME}.txt"
mkdir -p deployments

cat > "$DEPLOY_INFO_FILE" <<EOF
Client: ${CLIENT_NAME}
Droplet Name: ${DROPLET_NAME}
Droplet ID: ${DROPLET_ID}
IP Address: ${DROPLET_IP}
Image: ${IMAGE_NAME}
Size: ${SIZE}
Region: ${REGION}
Created: $(date)
EOF

echo -e "${GREEN}✓${NC} Deployment info saved to: $DEPLOY_INFO_FILE"
echo

# Wait for SSH to be ready
echo -e "${BLUE}Waiting for SSH to be ready...${NC}"
for i in {1..30}; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 qbmgr@${DROPLET_IP} "echo 'SSH Ready'" 2>/dev/null | grep -q "SSH Ready"; then
        echo -e "${GREEN}✓${NC} SSH is ready!"
        break
    fi
    echo -n "."
    sleep 10
done
echo

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo
echo "1. SSH to the droplet:"
echo "   ${YELLOW}ssh qbmgr@${DROPLET_IP}${NC}"
echo
echo "2. Start deploying clients:"
echo "   ${YELLOW}cd ~/open-webui/mt${NC}"
echo "   ${YELLOW}./client-manager.sh${NC}"
echo
echo "3. Or run deployment remotely:"
echo "   ${YELLOW}./remote-deploy.sh ${CLIENT_NAME} ${DROPLET_IP}${NC}"
echo
echo -e "${GREEN}✓${NC} Droplet is ready for client deployments!"
