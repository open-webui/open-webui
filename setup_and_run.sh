#!/bin/bash

# Open WebUI Setup and Run Script for Jason G
# This script sets up and runs both the backend and frontend of Open WebUI

set -e  # Exit on any error

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with colors
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check dependencies
check_dependencies() {
    info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &>/dev/null; then
        error "Python 3 is not installed. Please install Python 3.11 or later."
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ $(echo "$PYTHON_VERSION < 3.10" | bc) -eq 1 ]]; then
        error "Python version $PYTHON_VERSION is not supported. Please install Python 3.10 or later."
    fi
    
    # Check Node.js
    if ! command -v node &>/dev/null; then
        error "Node.js is not installed. Please install Node.js 18 or later."
    fi
    
    NODE_VERSION=$(node -v | cut -d 'v' -f 2)
    if [[ $(echo "$NODE_VERSION < 18.0.0" | bc) -eq 1 ]]; then
        error "Node.js version $NODE_VERSION is not supported. Please install Node.js 18 or later."
    fi
    
    # Check npm
    if ! command -v npm &>/dev/null; then
        error "npm is not installed. Please install npm."
    fi
    
    success "All dependencies are installed."
}

# Setup environment (.env file)
setup_environment() {
    info "Setting up environment..."
    
    if [ ! -f .env ]; then
        info "Creating .env file from .env.example"
        cp .env.example .env
        success "Created .env file. Please adjust the settings if needed."
    else
        info ".env file already exists. Using existing configuration."
    fi
}

# Setup backend
setup_backend() {
    info "Setting up backend..."
    
    # Create Python virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        info "Creating Python virtual environment..."
        python3 -m venv venv
        success "Created Python virtual environment."
    else
        info "Python virtual environment already exists."
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install backend dependencies
    info "Installing backend dependencies..."
    pip install -U pip wheel
    pip install -r backend/requirements.txt
    
    success "Backend setup completed."
}

# Setup frontend
setup_frontend() {
    info "Setting up frontend..."
    
    # Install frontend dependencies
    npm install
    
    success "Frontend setup completed."
}

# Run backend in development mode
run_backend_dev() {
    info "Starting backend in development mode..."
    
    # Change to backend directory
    cd backend
    
    # Make sure start.sh is executable
    chmod +x start.sh
    
    # Activate virtual environment and run backend
    source ../venv/bin/activate
    ./dev.sh
}

# Run frontend in development mode
run_frontend_dev() {
    info "Starting frontend in development mode..."
    
    # Run frontend in development mode
    npm run dev
}

# Main function
main() {
    info "Starting setup and run script for Open WebUI..."
    
    # Check if running in a terminal
    if [ ! -t 0 ]; then
        error "This script should be run in a terminal."
    fi
    
    # Check dependencies
    check_dependencies
    
    # Setup environment
    setup_environment
    
    # Setup backend
    setup_backend
    
    # Setup frontend
    setup_frontend
    
    # Ask for run mode
    echo ""
    echo "Please select how you want to run Open WebUI:"
    echo "1) Development mode (recommended for development)"
    echo "2) Exit after setup"
    
    read -p "Enter your choice (1-2): " RUN_MODE
    
    case $RUN_MODE in
        1)
            # Start backend and frontend in development mode
            # Use tmux to run both in the same terminal
            if command -v tmux &>/dev/null; then
                info "Starting backend and frontend using tmux..."
                
                tmux new-session -d -s openwebui
                tmux split-window -h -t openwebui
                
                tmux send-keys -t openwebui:0.0 "cd $(pwd) && bash -c 'source venv/bin/activate && cd backend && ./dev.sh'" C-m
                tmux send-keys -t openwebui:0.1 "cd $(pwd) && npm run dev" C-m
                
                success "Open WebUI is now running!"
                echo "Frontend: http://localhost:5173"
                echo "Backend: http://localhost:8080"
                echo ""
                echo "To view the running services, attach to the tmux session:"
                echo "$ tmux attach -t openwebui"
                echo ""
                echo "To detach from the tmux session without stopping the services: Press Ctrl+B then D"
                echo "To stop the services: Press Ctrl+C in each pane, or kill the tmux session with: tmux kill-session -t openwebui"
                
                tmux attach -t openwebui
            else
                warn "tmux is not installed. Starting backend only. You'll need to run the frontend separately."
                echo "To run the frontend, open another terminal and run: npm run dev"
                run_backend_dev
            fi
            ;;
        2)
            success "Setup completed. You can run the backend with: cd backend && ./dev.sh"
            success "You can run the frontend with: npm run dev"
            ;;
        *)
            error "Invalid choice. Exiting."
            ;;
    esac
}

# Run main function
main
