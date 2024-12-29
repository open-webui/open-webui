#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}ComfyUI Agent Plugin Development Installation${NC}"
echo "==========================================="

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

# Install development requirements
echo -e "\n${YELLOW}Installing development requirements...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install requirements${NC}"
    exit 1
fi

# Install package in development mode
echo -e "\n${YELLOW}Installing package in development mode...${NC}"
cd ..
pip install -e .
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install package${NC}"
    cd -
    exit 1
fi
cd -

# Create symbolic link to parent directory for imports
echo -e "\n${YELLOW}Creating symbolic links...${NC}"
PARENT_DIR=$(dirname $(dirname $(pwd)))
ln -sf "$PARENT_DIR/image_generation_agent.py" .
ln -sf "$PARENT_DIR/clip_scorer.py" .

# Create directories
echo -e "\n${YELLOW}Creating required directories...${NC}"
mkdir -p outputs test_outputs

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
python3 test_plugin.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Warning: Some tests failed${NC}"
else
    echo -e "${GREEN}All tests passed!${NC}"
fi

# Run LLM workflow test
echo -e "\n${YELLOW}Testing LLM workflow...${NC}"
python3 test_llm_workflow.py --save test_outputs/llm_test_conversation.json
if [ $? -ne 0 ]; then
    echo -e "${RED}Warning: LLM workflow test failed${NC}"
else
    echo -e "${GREEN}LLM workflow test passed!${NC}"
fi

echo -e "\n${GREEN}Development installation completed!${NC}"
echo -e "\nTo test the plugin:"
echo -e "1. Activate the virtual environment:"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo -e "\n2. Run Python and import the package:"
echo -e "   ${YELLOW}python3${NC}"
echo -e "   ${YELLOW}>>> import comfyui_agent${NC}"
echo -e "   ${YELLOW}>>> result = comfyui_agent.generate_image('A beautiful sunset')${NC}"
echo -e "\n3. Run the LLM workflow test:"
echo -e "   ${YELLOW}./test_llm_workflow.py${NC}"
echo -e "\nPlugin files are in: ${BLUE}$(pwd)${NC}"