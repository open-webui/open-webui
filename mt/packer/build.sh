#!/bin/bash
# Helper script to build Open WebUI golden image
# Usage: ./build.sh [DO_TOKEN]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Open WebUI Golden Image Builder (Packer)              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if packer is installed
if ! command -v packer &> /dev/null; then
    echo -e "${RED}❌ Packer is not installed${NC}"
    echo
    echo "Install Packer:"
    echo "  macOS:   brew install hashicorp/tap/packer"
    echo "  Linux:   https://www.packer.io/downloads"
    echo "  Windows: choco install packer"
    exit 1
fi

echo -e "${GREEN}✅ Packer version: $(packer version)${NC}"
echo

# Initialize Packer (download plugins)
echo -e "${BLUE}Initializing Packer plugins...${NC}"
if packer init open-webui-image.pkr.hcl; then
    echo -e "${GREEN}✅ Plugins initialized${NC}"
else
    echo -e "${RED}❌ Failed to initialize plugins${NC}"
    exit 1
fi
echo

# Get Digital Ocean token
if [ $# -ge 1 ]; then
    DO_TOKEN="$1"
    echo "Using provided Digital Ocean token"
elif [ -n "${DIGITALOCEAN_TOKEN:-}" ]; then
    DO_TOKEN="$DIGITALOCEAN_TOKEN"
    echo "Using DIGITALOCEAN_TOKEN environment variable"
else
    echo -e "${YELLOW}Digital Ocean API Token Required${NC}"
    echo
    echo "Get your token at: https://cloud.digitalocean.com/account/api/tokens"
    echo
    read -p "Enter your Digital Ocean API token: " DO_TOKEN
    if [ -z "$DO_TOKEN" ]; then
        echo -e "${RED}❌ No token provided${NC}"
        exit 1
    fi
fi

echo

# Optional: Set custom variables
echo -e "${BLUE}Build Configuration${NC}"
echo -e "${YELLOW}Press Enter to use defaults, or enter custom values:${NC}"
echo

read -p "Image name prefix (default: open-webui-multitenant): " IMAGE_NAME
IMAGE_NAME="${IMAGE_NAME:-open-webui-multitenant}"

read -p "Build region (default: nyc3): " REGION
REGION="${REGION:-nyc3}"

read -p "Droplet size (default: s-2vcpu-2gb): " SIZE
SIZE="${SIZE:-s-2vcpu-2gb}"

read -p "Repository branch (default: main): " BRANCH
BRANCH="${BRANCH:-main}"

echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo "Build Settings:"
echo "  Image Name: ${IMAGE_NAME}"
echo "  Region:     ${REGION}"
echo "  Size:       ${SIZE}"
echo "  Branch:     ${BRANCH}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo

read -p "Start build? (Y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "Build cancelled"
    exit 0
fi

echo
echo -e "${GREEN}Starting Packer build...${NC}"
echo "This will take 5-8 minutes"
echo

# Run Packer build
export DIGITALOCEAN_TOKEN="$DO_TOKEN"

if packer build \
    -var "image_name=${IMAGE_NAME}" \
    -var "region=${REGION}" \
    -var "size=${SIZE}" \
    -var "repo_branch=${BRANCH}" \
    open-webui-image.pkr.hcl; then

    echo
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Build Complete!${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo

    # Show manifest if available
    if [ -f manifest.json ]; then
        echo "Image details:"
        if command -v jq &> /dev/null; then
            cat manifest.json | jq -r '.builds[0].artifact_id'
        else
            cat manifest.json
        fi
        echo
    fi

    echo "Your custom image is now available in Digital Ocean:"
    echo "  Dashboard → Images → Custom Images"
    echo
    echo "To deploy a droplet from this image:"
    echo "  1. Create → Droplets"
    echo "  2. Choose an image → Custom Images tab"
    echo "  3. Select: ${IMAGE_NAME}-$(date +%Y-%m-%d)"
    echo
    echo "First boot: Add SSH key for qbmgr user (see README.md)"
    echo
else
    echo
    echo -e "${RED}❌ Build failed${NC}"
    echo "Check the output above for errors"
    echo
    echo "For detailed logs, run:"
    echo "  PACKER_LOG=1 packer build open-webui-image.pkr.hcl"
    exit 1
fi
