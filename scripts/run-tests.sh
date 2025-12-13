#!/bin/bash

# Mermaid Test Runner Script
# Uses conda environment rit4test and Docker for comprehensive testing

set -e

echo "========================================="
echo "Mermaid Scalability Test Suite"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed${NC}"
    exit 1
fi

# Activate conda environment
echo -e "${YELLOW}Activating conda environment: rit4test${NC}"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate rit4test || {
    echo -e "${YELLOW}Environment rit4test not found, creating...${NC}"
    conda create -n rit4test python=3.10 -y
    conda activate rit4test
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Warning: Docker is not available, running tests locally${NC}"
    USE_DOCKER=false
else
    USE_DOCKER=true
    echo -e "${GREEN}Docker is available${NC}"
fi

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
fi

# Run tests
echo -e "${GREEN}Starting test suite...${NC}"

if [ "$USE_DOCKER" = true ]; then
    echo -e "${YELLOW}Running tests in Docker...${NC}"
    
    # Build test image
    docker build -f Dockerfile.test -t mermaid-test:latest .
    
    # Run unit tests
    echo -e "${GREEN}Running unit tests...${NC}"
    docker run --rm -v $(pwd):/app -w /app mermaid-test:latest npm run test:unit
    
    # Run integration tests
    echo -e "${GREEN}Running integration tests...${NC}"
    docker run --rm -v $(pwd):/app -w /app mermaid-test:latest npm run test:integration
    
    # Run E2E tests
    echo -e "${GREEN}Running E2E tests...${NC}"
    docker-compose -f docker-compose.test.yaml up --abort-on-container-exit test-browser
else
    echo -e "${YELLOW}Running tests locally...${NC}"
    
    # Run unit tests
    echo -e "${GREEN}Running unit tests...${NC}"
    npm run test:unit
    
    # Run integration tests
    echo -e "${GREEN}Running integration tests...${NC}"
    npm run test:integration
    
    # Run E2E tests
    echo -e "${GREEN}Running E2E tests...${NC}"
    npm run test:e2e
fi

# Generate coverage report
echo -e "${GREEN}Generating coverage report...${NC}"
npm run test:coverage

echo -e "${GREEN}========================================="
echo "All tests completed!"
echo "=========================================${NC}"

