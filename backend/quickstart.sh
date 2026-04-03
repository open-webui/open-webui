#!/usr/bin/env bash

# Quickstart script for backend development after initial SSH into host
# Assumes repository is already cloned at /home/zbrad/gh/open-webui

set -e

# Change to backend directory
cd "$(dirname "$0")" || exit 1

# Function to check if virtual environment is already activated
is_venv_active() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "Virtual environment is already activated: $VIRTUAL_ENV"
        return 0  # true
    fi
    return 1  # false
}

# Function to activate virtual environment
activate_venv() {
    if [ -d ".venv" ]; then
        echo "Activating virtual environment..."
        source .venv/bin/activate
        return 0  # true
    else
        echo "Virtual environment not found at .venv"
        return 1  # false
    fi
}

# Function to setup virtual environment
setup_venv() {
    echo "Setting up virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
}

# Main logic
if is_venv_active; then
    # VENV is already active, no action needed
    :
elif activate_venv; then
    # Successfully activated existing venv
    :
else
    # Need to create and setup venv
    setup_venv
fi

# Set development environment variables
export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
export USER_AGENT="open-webui-agent"
export PORT="${PORT:-8080}"
export HOST="${HOST:-0.0.0.0}"
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"

# Start the development server with auto-reload
echo "Starting Open WebUI backend development server on $HOST:$PORT..."
uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --reload --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"