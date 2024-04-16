#!/bin/bash

# Parse command-line arguments for the --no-docker flag
for arg in "$@"
do
    case $arg in
        --no-docker)
        NO_DOCKER=1
        shift # Remove --no-docker from processing
        ;;
        *)
        # Unknown option
        ;;
    esac
done

# Function to check if Docker is installed
check_docker() {
    echo "Checking for Docker..."
    if ! command -v docker &> /dev/null; then
        echo "Docker could not be found. Would you like to install Docker? (y/n)"
        read -r choice
        if [ "$choice" = "y" ]; then
            install_docker
        else
            echo "Docker is required for the Docker-based installation."
            echo "Would you like to proceed with the Docker-less installation? (y/N)"
            read -r proceed
            if [ "$proceed" != "y" ]; then
                echo "Exiting the installation script."
                exit 0
            fi
            dockerless_install
            exit 0
        fi
    else
        echo "Docker is already installed."
    fi
}

# Function to install Docker
install_docker() {
    echo "Installing Docker..."
    curl -fsSL get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo docker run --rm hello-world
    if [ $? -ne 0 ]; then
        echo "Docker installation failed. Please check the error messages above."
        exit 1
    fi
    echo "Docker has been successfully installed."
}

# Function to install Node.js using nvm
install_nodejs() {
    echo "Node.js not found. Installing Node.js using nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
    source "$HOME/.nvm/nvm.sh"
    nvm install 20
}

# Function to install Miniconda for Python
install_miniconda() {
    echo "Installing Miniconda for Python dependencies..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda
    source "$HOME/miniconda/etc/profile.d/conda.sh"
    conda init
    conda create -y -n openwebui python=3.11
    conda activate openwebui
}

# Function for Docker-less installation
dockerless_install() {
    echo "Starting Docker-less installation..."
    
    # Node.js Installation
    if ! command -v node &> /dev/null; then
        install_nodejs
    fi

    # Miniconda and Python Environment Setup
    install_miniconda

    cp -RPp .env.example .env

    if command -v npm &> /dev/null; then
        npm install
        npm run build
    else
        echo "npm is not available after Node.js installation. Exiting."
        exit 1
    fi

    cd ./backend
    pip install -r requirements.txt -U
    sh start.sh
    echo "Open WebUI has been installed and started without Docker."
}

# Function to install Open WebUI with Docker
install_openwebui_docker() {
    echo "Installing Open WebUI with Docker..."
    docker pull ghcr.io/open-webui/open-webui:latest
    docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:latest
    echo "Open WebUI has been installed and started with Docker. Access it at http://localhost:3000"
}

# Main script starts here
echo "Starting the Open WebUI installation script..."

if [ -n "$NO_DOCKER" ] && [ "$NO_DOCKER" -eq 1 ]; then
    echo "Proceeding with Docker-less installation due to --no-docker flag."
    dockerless_install
    echo "Installation process has completed."
    exit 0
fi

# Step 1: Check for Docker
check_docker

# Step 2: Ask about Ollama installation
echo "Would you like to install Ollama inside Docker? (y/n)"
read -r install_ollama

if [ "$install_ollama" = "y" ]; then
    # Commands to install Ollama in Docker go here.
    echo "Do you want Ollama in Docker with GPU support? (y/n): "
    read -r use_gpu
    echo "Installing Ollama with Docker..."
    if [ "$use_gpu" = "y" ]; then
        ./run-ollama-docker.sh --enable-gpu
    else
        ./run-ollama-docker.sh
    fi
else
    # If not installing Ollama, ask about using Docker Compose for both
    echo "Would you like to deploy Open WebUI and Ollama together using Docker Compose? (y/n)"
    read -r deploy_compose

    if [ "$deploy_compose" = "y" ]; then
        echo "Enable GPU support? (y/n)"
        read -r enable_gpu

        compose_cmd="./run-compose.sh"

        if [ "$enable_gpu" = "y" ]; then
            compose_cmd+=" --enable-gpu"
        fi

        echo "Running: $compose_cmd"
        eval "$compose_cmd"
    else
        # If not using Docker Compose, install Open WebUI with Docker alone
        install_openwebui_docker
    fi
fi

echo "Installation process has completed."
