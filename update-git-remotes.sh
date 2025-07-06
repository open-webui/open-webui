#!/bin/bash

# Script to update git remotes for xynthorai-open-webui

echo "Updating Git remotes..."

# Remove old origin
git remote remove origin

# Add new origin
git remote add origin https://github.com/ipdeepdive/open-webui.git

# Verify upstream is still correct
git remote get-url upstream || git remote add upstream https://github.com/open-webui/open-webui.git

# Set upstream push to disabled (to prevent accidental pushes)
git remote set-url --push upstream DISABLE

# Show new configuration
echo ""
echo "New remote configuration:"
git remote -v

echo ""
echo "Done! You can now push to the new repository with:"
echo "git push -u origin custom-xynthor-integration"