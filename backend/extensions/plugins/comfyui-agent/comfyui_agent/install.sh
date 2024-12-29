#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}ComfyUI Agent Plugin Installer${NC}"
echo "================================"

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python3 --version
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check if pip is installed
echo -e "\n${YELLOW}Checking pip installation...${NC}"
python3 -m pip --version
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: pip is not installed${NC}"
    exit 1
fi

# Check if ComfyUI is running
echo -e "\n${YELLOW}Checking ComfyUI connection...${NC}"
curl -s "http://127.0.0.1:8188/history" > /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Warning: ComfyUI is not running${NC}"
    echo -e "Please make sure ComfyUI is running on port 8188"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "\n${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to activate virtual environment${NC}"
    exit 1
fi

# Install requirements
echo -e "\n${YELLOW}Installing requirements...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install requirements${NC}"
    exit 1
fi

# Install plugin in development mode
echo -e "\n${YELLOW}Installing plugin...${NC}"
pip install -e .
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install plugin${NC}"
    exit 1
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p outputs
mkdir -p test_outputs

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
python3 test_plugin.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Warning: Some tests failed${NC}"
else
    echo -e "${GREEN}All tests passed!${NC}"
fi

echo -e "\n${GREEN}Installation completed!${NC}"
echo -e "\nTo use the plugin in Open WebUI:"
echo -e "1. Make sure ComfyUI is running: ${BLUE}python path/to/ComfyUI/main.py${NC}"
echo -e "2. Restart Open WebUI"
echo -e "3. The plugin functions will be available to your LLM:"
echo -e "   - ${YELLOW}generate_image${NC}"
echo -e "   - ${YELLOW}analyze_image${NC}"
echo -e "\nFor examples and documentation, see: ${BLUE}README.md${NC}"