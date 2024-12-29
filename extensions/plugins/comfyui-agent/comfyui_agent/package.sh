#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VERSION=$(grep '"version":' config.json | head -1 | cut -d'"' -f4)
PLUGIN_NAME="comfyui-agent"
PACKAGE_NAME="${PLUGIN_NAME}-${VERSION}"
DIST_DIR="../dist"

echo -e "${BLUE}Packaging ComfyUI Agent Plugin v${VERSION}${NC}"
echo "=================================="

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
    config.json \
    manifest.json \
    requirements.txt \
    setup.py \
    README.md \
    examples.py \
    test_plugin.py \
    install.sh \
    "$PACKAGE_DIR/"

# Create source distribution
echo -e "\n${YELLOW}Creating source distribution...${NC}"
python3 setup.py sdist bdist_wheel
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create source distribution${NC}"
    exit 1
fi

# Create tarball
echo -e "\n${YELLOW}Creating tarball...${NC}"
cd "$TEMP_DIR"
tar czf "$DIST_DIR/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create tarball${NC}"
    exit 1
fi

# Copy wheel
echo -e "\n${YELLOW}Copying wheel...${NC}"
cp dist/*.whl "$DIST_DIR/"

# Clean up
rm -rf "$TEMP_DIR" build/ dist/ *.egg-info/

echo -e "\n${GREEN}Package created successfully!${NC}"
echo -e "\nPackage files:"
echo -e "1. ${BLUE}${DIST_DIR}/${PACKAGE_NAME}.tar.gz${NC} (source distribution)"
echo -e "2. ${BLUE}${DIST_DIR}/${PACKAGE_NAME}*.whl${NC} (wheel distribution)"

echo -e "\nTo install the plugin:"
echo -e "1. Using pip:"
echo -e "   ${YELLOW}pip install ${DIST_DIR}/${PACKAGE_NAME}.tar.gz${NC}"
echo -e "\n2. Manual installation:"
echo -e "   ${YELLOW}tar xzf ${DIST_DIR}/${PACKAGE_NAME}.tar.gz${NC}"
echo -e "   ${YELLOW}cd ${PACKAGE_NAME}${NC}"
echo -e "   ${YELLOW}./install.sh${NC}"

echo -e "\nPlugin will be available in Open WebUI after installation and restart."