#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "\nUsage: $0 [docker|standard]"
    echo -e "\nOptions:"
    echo "  docker    - Switch to Docker environment"
    echo "  standard  - Switch to standard environment"
    echo -e "\nExample:"
    echo "  $0 docker"
}

# Function to switch to Docker environment
switch_to_docker() {
    echo -e "\n${YELLOW}Switching to Docker environment...${NC}"
    
    # Create symbolic link to Docker config
    ln -sf docker_config.json active_config.json
    
    # Update environment variables
    cat > .env << EOF
COMFYUI_API_URL=http://comfyui:8188
COMFYUI_OUTPUT_DIR=/app/data/outputs
PLUGIN_CACHE_DIR=/app/data/cache
COMFYUI_MODEL_DIR=/app/comfyui/models
EOF
    
    echo -e "${GREEN}✓ Switched to Docker environment${NC}"
    echo -e "\nTo verify setup:"
    echo -e "1. Run Docker tests:"
    echo -e "   ${BLUE}./docker_test.sh${NC}"
    echo -e "2. Check configuration:"
    echo -e "   ${BLUE}cat active_config.json${NC}"
}

# Function to switch to standard environment
switch_to_standard() {
    echo -e "\n${YELLOW}Switching to standard environment...${NC}"
    
    # Create symbolic link to standard config
    ln -sf config.json active_config.json
    
    # Update environment variables
    cat > .env << EOF
COMFYUI_API_URL=http://127.0.0.1:8188
COMFYUI_OUTPUT_DIR=outputs
PLUGIN_CACHE_DIR=cache
COMFYUI_MODEL_DIR=models
EOF
    
    echo -e "${GREEN}✓ Switched to standard environment${NC}"
    echo -e "\nTo verify setup:"
    echo -e "1. Run tests:"
    echo -e "   ${BLUE}./test_plugin.py${NC}"
    echo -e "2. Check configuration:"
    echo -e "   ${BLUE}cat active_config.json${NC}"
}

# Main script
case "$1" in
    "docker")
        switch_to_docker
        ;;
    "standard")
        switch_to_standard
        ;;
    *)
        echo -e "${RED}Error: Invalid or missing argument${NC}"
        show_usage
        exit 1
        ;;
esac

# Print current configuration
echo -e "\n${YELLOW}Current configuration:${NC}"
echo -e "Environment: ${BLUE}$1${NC}"
echo -e "Config file: ${BLUE}active_config.json${NC}"
echo -e "Environment variables:"
cat .env

echo -e "\n${GREEN}Done!${NC}"
