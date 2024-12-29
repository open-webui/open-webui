#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VERSION=$(grep '"version":' config.json | head -1 | cut -d'"' -f4)
PLUGIN_NAME="comfyui-agent"
PACKAGE_NAME="${PLUGIN_NAME}-${VERSION}-docker"
DIST_DIR="../dist"

echo -e "${BLUE}Packaging ComfyUI Agent Plugin v${VERSION} for Docker${NC}"
echo "=================================================="

# Create distribution directory
mkdir -p "$DIST_DIR"

# Clean previous builds
echo -e "\n${YELLOW}Cleaning previous builds...${NC}"
rm -rf "$DIST_DIR/${PACKAGE_NAME}"* build/ dist/ *.egg-info/

# Create temporary directory for package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/${PACKAGE_NAME}"
mkdir -p "$PACKAGE_DIR"

# Copy files
echo -e "\n${YELLOW}Copying files...${NC}"
cp -r \
    __init__.py \
    plugin.py \
    docker_init.py \
    docker_config.json \
    config.json \
    manifest.json \
    requirements.txt \
    README.md \
    test_docker.py \
    docker_test.sh \
    "$PACKAGE_DIR/"

# Create Docker-specific README
echo -e "\n${YELLOW}Creating Docker documentation...${NC}"
cat > "$PACKAGE_DIR/DOCKER_README.md" << EOL
# ComfyUI Agent Plugin - Docker Installation

This is the Docker-ready version of the ComfyUI Agent Plugin for Open WebUI.

## Quick Installation

1. Copy this directory to your Open WebUI plugins directory:
\`\`\`bash
cp -r ${PACKAGE_NAME} /path/to/open-webui/extensions/plugins/
\`\`\`

2. Update your docker-compose.yml:
\`\`\`yaml
services:
  open-webui:
    volumes:
      - ./extensions/plugins/${PLUGIN_NAME}:/app/extensions/plugins/${PLUGIN_NAME}
    environment:
      - COMFYUI_API_URL=http://comfyui:8188
\`\`\`

3. Restart Open WebUI:
\`\`\`bash
docker-compose restart open-webui
\`\`\`

4. Test the installation:
\`\`\`bash
cd /path/to/open-webui/extensions/plugins/${PLUGIN_NAME}
./docker_test.sh
\`\`\`

## Environment Variables

- \`COMFYUI_API_URL\`: URL of the ComfyUI API (default: http://comfyui:8188)
- \`COMFYUI_OUTPUT_DIR\`: Directory for generated images (default: /app/data/outputs)
- \`PLUGIN_CACHE_DIR\`: Directory for plugin cache (default: /app/data/cache)

## Directory Structure

\`\`\`
${PLUGIN_NAME}/
├── __init__.py           # Plugin initialization
├── plugin.py            # Main plugin code
├── docker_init.py       # Docker initialization
├── docker_config.json   # Docker configuration
├── config.json         # Plugin configuration
├── manifest.json       # Plugin manifest
├── requirements.txt    # Python dependencies
├── test_docker.py     # Docker tests
└── docker_test.sh     # Test script
\`\`\`

## Troubleshooting

1. Check ComfyUI connection:
\`\`\`bash
curl http://localhost:8188/history
\`\`\`

2. Check plugin installation:
\`\`\`bash
docker exec open-webui ls -la /app/extensions/plugins/${PLUGIN_NAME}
\`\`\`

3. Check logs:
\`\`\`bash
docker-compose logs open-webui
docker-compose logs comfyui
\`\`\`

## Support

For issues and support, please visit:
- GitHub Issues: [Report Issues](https://github.com/yourusername/comfyui-agent/issues)
- Documentation: See DOCKER_SETUP.md in the main repository
EOL

# Create tarball
echo -e "\n${YELLOW}Creating tarball...${NC}"
cd "$TEMP_DIR"
tar czf "$DIST_DIR/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create tarball${NC}"
    exit 1
fi

# Clean up
rm -rf "$TEMP_DIR"

echo -e "\n${GREEN}Package created successfully!${NC}"
echo -e "\nPackage file:"
echo -e "${BLUE}${DIST_DIR}/${PACKAGE_NAME}.tar.gz${NC}"

echo -e "\nTo install in Docker environment:"
echo -e "1. Extract the package:"
echo -e "   ${YELLOW}tar xzf ${PACKAGE_NAME}.tar.gz${NC}"
echo -e "2. Copy to Open WebUI plugins directory:"
echo -e "   ${YELLOW}cp -r ${PACKAGE_NAME} /path/to/open-webui/extensions/plugins/${NC}"
echo -e "3. Update docker-compose.yml with the provided configuration"
echo -e "4. Restart Open WebUI:"
echo -e "   ${YELLOW}docker-compose restart open-webui${NC}"
echo -e "5. Run tests:"
echo -e "   ${YELLOW}./docker_test.sh${NC}"