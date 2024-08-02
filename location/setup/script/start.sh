#!/bin/bash
CONDA_BASE=$(conda info --base)
# Exit immediately if a command exits with a non-zero status.
set -e

# Install npm dependencies and build the project
echo "Running npm install..."
npm install

echo "Running npm build..."
npm run build

echo "npm install and build completed"

# Navigate to the backend directory
echo "Navigating to backend directory..."
cd ./backend

# Check if conda is installed
source $CONDA_BASE/etc/profile.d/conda.sh
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