#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

CONDA_BASE=$(conda info --base)
if [ -z "$CONDA_BASE" ]; then
  echo "Conda base path not found."
  exit 1
fi
echo "CONDA_BASE:" $CONDA_BASE

# Install npm dependencies and build the project
echo "Running npm install..."
npm install

echo "Running npm build..."
npm run build

echo "npm install and build completed"

# Navigate to the backend directory
echo "Navigating to backend directory..."
cd ./backend

# Check if conda is installed by sourcing the conda initialization script
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/opt/miniconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/opt/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/opt/anaconda3/etc/profile.d/conda.sh"
else
    echo "Conda initialization script not found. Please install Conda and ensure it is properly initialized."
    exit 1
fi

# Check if conda is installed
if command -v conda &> /dev/null
then
    echo "Conda is installed. Proceeding to create and activate the Conda environment."
    # Create and activate the Conda environment
    echo "Creating Conda environment..."
    conda create --name open-webui-env python=3.11

    echo "Activating Conda environment..."
    conda activate open-webui-env

    # Install Python dependencies using pip
    echo "Installing Python dependencies..."
    pip install -r requirements.txt -U

    echo "Python dependencies installed."
    echo "Starting the application..."
    bash start.sh
else
    echo "Conda is not installed. Please install Conda and try again."
    exit 1
fi

echo "Script completed successfully."