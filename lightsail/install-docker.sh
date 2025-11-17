#!/bin/bash

# Docker Installation Script for AWS Lightsail (Ubuntu)
# Usage: ./install-docker.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

print_status "🐳 Starting Docker installation on AWS Lightsail..."

# Step 1: Update system
print_status "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated successfully"

# Step 2: Install prerequisites
print_status "Step 2: Installing prerequisites..."
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
print_success "Prerequisites installed"

# Step 3: Install Docker
print_status "Step 3: Installing Docker..."
if ! command_exists docker; then
    # Download and run Docker installation script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Clean up
    rm get-docker.sh
    
    print_success "Docker installed successfully"
else
    print_warning "Docker is already installed"
fi

# Step 4: Install Docker Compose
print_status "Step 4: Installing Docker Compose..."
if ! command_exists docker-compose; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed successfully"
else
    print_warning "Docker Compose is already installed"
fi

# Step 5: Start and enable Docker service
print_status "Step 5: Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker
print_success "Docker service started and enabled"

# Step 6: Verify installation
print_status "Step 6: Verifying installation..."
DOCKER_VERSION=$(docker --version)
COMPOSE_VERSION=$(docker-compose --version)

echo ""
echo "=========================================="
print_success "🎉 DOCKER INSTALLATION COMPLETED! 🎉"
echo "=========================================="
echo ""
echo -e "${GREEN}Installation Summary:${NC}"
echo -e "  🐳 Docker: ${YELLOW}$DOCKER_VERSION${NC}"
echo -e "  🔧 Docker Compose: ${YELLOW}$COMPOSE_VERSION${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. ${YELLOW}Log out and log back in${NC} for group changes to take effect"
echo -e "  2. Test Docker: ${YELLOW}docker run hello-world${NC}"
echo -e "  3. Test Docker Compose: ${YELLOW}docker-compose --version${NC}"
echo ""
echo -e "${BLUE}Useful Docker Commands:${NC}"
echo -e "  📊 List containers: ${YELLOW}docker ps${NC}"
echo -e "  📋 List images: ${YELLOW}docker images${NC}"
echo -e "  🧹 Clean up: ${YELLOW}docker system prune${NC}"
echo -e "  📖 Get help: ${YELLOW}docker --help${NC}"
echo ""
print_warning "⚠️  You need to log out and log back in for Docker group permissions to take effect!"
echo ""
print_success "Docker installation completed successfully!"
