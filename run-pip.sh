#!/bin/bash

# Check if Python 3.11 is installed
if command -v python3.11 &> /dev/null; then
    echo "Python 3.11 is already installed."
else
    echo "Installing Python 3.11..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv
fi

# Create and activate the virtual environment
ENV_DIR="myenv"
if [ ! -d "$ENV_DIR" ]; then
    echo "Creating a virtual environment..."
    python3.11 -m venv "$ENV_DIR"
fi

# Activate the virtual environment
source "$ENV_DIR/bin/activate"

# Install open-webui
echo "Installing open-webui..."
pip install open-webui

# Run open-webui
echo "Running open-webui..."
open-webui serve
