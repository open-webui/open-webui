#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}ComfyUI Agent Plugin - Docker Environment Test${NC}"
echo "=============================================="

# Function to check Docker installation
check_docker() {
    echo -e "\n${YELLOW}Checking Docker installation...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker is not installed${NC}"
        echo "Please install Docker first:"
        echo "https://docs.docker.com/get-docker/"
        return 1
    fi
    echo -e "${GREEN}✓ Docker is installed${NC}"
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗ Docker Compose is not installed${NC}"
        echo "Please install Docker Compose:"
        echo "https://docs.docker.com/compose/install/"
        return 1
    fi
    echo -e "${GREEN}✓ Docker Compose is installed${NC}"
    
    return 0
}

# Function to check NVIDIA Docker support
check_nvidia_docker() {
    echo -e "\n${YELLOW}Checking NVIDIA Docker support...${NC}"
    
    if ! command -v nvidia-smi &> /dev/null; then
        echo -e "${RED}✗ NVIDIA drivers not found${NC}"
        echo "Please install NVIDIA drivers first"
        return 1
    fi
    echo -e "${GREEN}✓ NVIDIA drivers found${NC}"
    
    # Test NVIDIA Docker
    if ! docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo -e "${RED}✗ NVIDIA Docker support not working${NC}"
        echo "Please install NVIDIA Container Toolkit:"
        echo "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        return 1
    fi
    echo -e "${GREEN}✓ NVIDIA Docker support working${NC}"
    
    return 0
}

# Function to check Open WebUI container
check_openwebui() {
    echo -e "\n${YELLOW}Checking Open WebUI container...${NC}"
    
    if ! docker ps | grep -q "open-webui"; then
        echo -e "${RED}✗ Open WebUI container not running${NC}"
        echo "Please start Open WebUI first:"
        echo "docker-compose up -d"
        return 1
    fi
    echo -e "${GREEN}✓ Open WebUI container running${NC}"
    
    # Check plugin directory
    if ! docker exec open-webui test -d /app/extensions/plugins/comfyui-agent; then
        echo -e "${RED}✗ Plugin directory not found in Open WebUI container${NC}"
        echo "Please check plugin installation"
        return 1
    fi
    echo -e "${GREEN}✓ Plugin directory found${NC}"
    
    return 0
}

# Function to check ComfyUI container
check_comfyui() {
    echo -e "\n${YELLOW}Checking ComfyUI container...${NC}"
    
    if ! docker ps | grep -q "comfyui"; then
        echo -e "${RED}✗ ComfyUI container not running${NC}"
        echo "Please start ComfyUI first:"
        echo "docker-compose up -d"
        return 1
    fi
    echo -e "${GREEN}✓ ComfyUI container running${NC}"
    
    # Check API access
    if ! curl -s "http://localhost:8188/history" > /dev/null; then
        echo -e "${RED}✗ Cannot access ComfyUI API${NC}"
        echo "Please check ComfyUI logs:"
        echo "docker-compose logs comfyui"
        return 1
    fi
    echo -e "${GREEN}✓ ComfyUI API accessible${NC}"
    
    return 0
}

# Function to check model files
check_models() {
    echo -e "\n${YELLOW}Checking model files...${NC}"
    
    # Check if models directory exists
    if ! docker exec comfyui test -d /app/comfyui/models; then
        echo -e "${RED}✗ Models directory not found${NC}"
        return 1
    fi
    
    # Check for model files
    model_count=$(docker exec comfyui sh -c "ls -1 /app/comfyui/models/*.ckpt /app/comfyui/models/*.safetensors 2>/dev/null | wc -l")
    if [ "$model_count" -eq 0 ]; then
        echo -e "${RED}✗ No model files found${NC}"
        echo "Please download required models:"
        echo "./manage_models.py --download v1-5-pruned.ckpt"
        return 1
    fi
    echo -e "${GREEN}✓ Found $model_count model files${NC}"
    
    return 0
}

# Function to run plugin tests
run_plugin_tests() {
    echo -e "\n${YELLOW}Running plugin tests...${NC}"
    
    # Run test script in container
    if ! docker exec open-webui python3 /app/extensions/plugins/comfyui-agent/test_docker.py; then
        echo -e "${RED}✗ Plugin tests failed${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Plugin tests passed${NC}"
    
    return 0
}

# Main test sequence
main() {
    # Check basic requirements
    check_docker || exit 1
    check_nvidia_docker || echo -e "${YELLOW}⚠ Warning: No GPU support available${NC}"
    
    # Check containers
    check_openwebui || exit 1
    check_comfyui || exit 1
    
    # Check models
    check_models || exit 1
    
    # Run plugin tests
    run_plugin_tests || exit 1
    
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo -e "\nYou can now use the ComfyUI Agent Plugin in Open WebUI."
    echo -e "Try generating an image with:"
    echo -e "${BLUE}curl -X POST http://localhost:8080/api/generate \\"
    echo -e "  -H 'Content-Type: application/json' \\"
    echo -e "  -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Generate an image of a beautiful sunset\"}]}'${NC}"
}

# Run main function
main