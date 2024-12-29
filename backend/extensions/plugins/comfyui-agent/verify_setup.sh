#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section header
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
    echo "----------------------------------------"
}

# Function to check command existence
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2 (command '$1' not found)"
        return 1
    fi
}

# Function to check Python package
check_package() {
    if python3 -c "import $1" &> /dev/null; then
        version=$(python3 -c "import $1; print($1.__version__)" 2>/dev/null || echo "version unknown")
        echo -e "${GREEN}✓${NC} $2 ($version)"
        return 0
    else
        echo -e "${RED}✗${NC} $2 (package '$1' not found)"
        return 1
    fi
}

# Function to check file existence
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2 (file not found)"
        return 1
    fi
}

# Function to check directory existence
check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2 (directory not found)"
        return 1
    fi
}

# Function to check if running in Docker
is_docker() {
    if [ -f /.dockerenv ]; then
        echo -e "${BLUE}Running in Docker environment${NC}"
        return 0
    else
        echo -e "${BLUE}Running in standard environment${NC}"
        return 1
    fi
}

# Start verification
echo -e "${BLUE}ComfyUI Agent Plugin - Setup Verification${NC}"
echo "=============================================="

# Check environment
print_header "Environment"
is_docker
echo "Python version: $(python3 --version)"
echo "Working directory: $(pwd)"

# Check system requirements
print_header "System Requirements"
check_command python3 "Python 3"
check_command pip3 "Pip package manager"
check_command git "Git version control"
check_command curl "Curl utility"

if ! is_docker; then
    check_command nvidia-smi "NVIDIA GPU support"
fi

# Check Python packages
print_header "Python Packages"
check_package torch "PyTorch"
check_package transformers "Transformers"
check_package PIL "Pillow imaging library"
check_package numpy "NumPy"
check_package requests "Requests library"
check_package tqdm "TQDM progress bars"
check_package huggingface_hub "Hugging Face Hub"

# Check plugin files
print_header "Plugin Files"
check_file "comfyui_agent/__init__.py" "Plugin initialization"
check_file "comfyui_agent/plugin.py" "Main plugin code"
check_file "comfyui_agent/config.json" "Configuration file"
check_file "comfyui_agent/requirements.txt" "Requirements file"

# Check directories
print_header "Directories"
check_directory "comfyui_agent" "Plugin directory"
check_directory "outputs" "Outputs directory"
check_directory "cache" "Cache directory"
check_directory "example_images" "Example images directory"

# Check ComfyUI connection
print_header "ComfyUI Connection"
if is_docker; then
    COMFYUI_URL="http://comfyui:8188"
else
    COMFYUI_URL="http://127.0.0.1:8188"
fi

if curl -s "$COMFYUI_URL/history" &> /dev/null; then
    echo -e "${GREEN}✓${NC} ComfyUI is running and accessible"
else
    echo -e "${RED}✗${NC} Cannot connect to ComfyUI at $COMFYUI_URL"
fi

# Run plugin tests
print_header "Plugin Tests"
if is_docker; then
    echo "Running Docker tests..."
    ./comfyui_agent/docker_test.sh
else
    echo "Running standard tests..."
    python3 comfyui_agent/test_plugin.py
fi

# Generate report
print_header "Setup Report"
echo "Date: $(date)"
echo "Environment: $(is_docker && echo 'Docker' || echo 'Standard')"
echo "Python: $(python3 --version)"
if ! is_docker && command -v nvidia-smi &> /dev/null; then
    echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
fi
echo "ComfyUI URL: $COMFYUI_URL"

# Print next steps
print_header "Next Steps"
echo "1. Read the documentation:"
echo "   - README.md for overview"
echo "   - QUICKSTART.md for getting started"
echo "   - DOCKER_SETUP.md for Docker setup"
echo ""
echo "2. Try generating an example image:"
echo "   ./run.sh --examples"
echo ""
echo "3. For issues or support:"
echo "   - Check INSTALL.md for troubleshooting"
echo "   - Submit issues on GitHub"
echo ""
echo -e "${GREEN}Setup verification completed!${NC}"