#!/bin/bash

# Test script for Open WebUI Homebrew formula
# This script tests installation, functionality, and uninstallation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing Open WebUI Homebrew Formula${NC}"
echo "======================================="

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# Check if we're in the right directory
if [ ! -f "open-webui.rb" ]; then
    echo -e "${RED}Error: open-webui.rb not found. Please run this script from the homebrew directory.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Checking formula syntax${NC}"
ruby -c open-webui.rb
print_result $? "Formula syntax check"

echo -e "\n${YELLOW}Step 2: Testing installation${NC}"
brew install --formula ./open-webui.rb
print_result $? "Formula installation"

echo -e "\n${YELLOW}Step 3: Testing CLI functionality${NC}"
which open-webui > /dev/null
print_result $? "open-webui command available"

open-webui --help > /dev/null
print_result $? "open-webui --help command"

open-webui serve --help > /dev/null
print_result $? "open-webui serve --help command"

echo -e "\n${YELLOW}Step 4: Testing uninstallation${NC}"
brew uninstall open-webui
print_result $? "Formula uninstallation"

# Verify it's completely removed
if which open-webui > /dev/null 2>&1; then
    echo -e "${RED}✗ open-webui command still available after uninstall${NC}"
    exit 1
else
    echo -e "${GREEN}✓ open-webui command properly removed${NC}"
fi

echo -e "\n${YELLOW}Step 5: Testing reinstallation${NC}"
brew install --formula ./open-webui.rb
print_result $? "Formula reinstallation"

open-webui --help > /dev/null
print_result $? "open-webui functionality after reinstall"

echo -e "\n${GREEN}All tests passed! 🎉${NC}"
echo -e "The Open WebUI Homebrew formula is working correctly."
echo -e "\nTo clean up after testing, run:"
echo -e "  ${YELLOW}brew uninstall open-webui${NC}"