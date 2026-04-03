#!/bin/bash

# Script to update to the latest version

set -e

echo "Updating to latest version..."

# Add your update logic here
pip install -q pip-chill
pip-chill --no-version --no-chill > $OPEN_WEBUI_ROOT/backend/req_latest.txt 

echo "Update complete!"