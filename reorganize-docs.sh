#!/bin/bash
# mAI Documentation Reorganization Script
# This script reorganizes documentation into a cleaner structure

echo "mAI Documentation Reorganization"
echo "================================"
echo ""
echo "This script will reorganize documentation into a cleaner structure:"
echo ""
echo "New structure:"
echo "  docs/"
echo "  ├── deployment/"
echo "  ├── development/"
echo "  ├── customization/"
echo "  ├── operations/"
echo "  └── configuration/"
echo ""
read -p "Do you want to proceed? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating new directory structure..."
    
    # Create new directories
    mkdir -p docs/deployment
    mkdir -p docs/development
    mkdir -p docs/customization
    mkdir -p docs/operations
    mkdir -p docs/configuration
    
    echo "Moving files to new locations..."
    
    # Move deployment docs
    [ -f "deployments/docs/HETZNER-DEPLOYMENT-GUIDE.md" ] && mv -v "deployments/docs/HETZNER-DEPLOYMENT-GUIDE.md" "docs/deployment/hetzner-guide.md"
    
    # Move development docs
    [ -f "docs/CONTRIBUTING.md" ] && mv -v "docs/CONTRIBUTING.md" "docs/development/contributing.md"
    [ -f "UPGRADE-GUIDE.md" ] && mv -v "UPGRADE-GUIDE.md" "docs/development/upgrade-guide.md"
    [ -f "README-dev-scripts.md" ] && mv -v "README-dev-scripts.md" "docs/development/development-scripts.md"
    
    # Move customization docs
    [ -f "MAI-CHANGELOG.md" ] && mv -v "MAI-CHANGELOG.md" "docs/customization/mai-changelog.md"
    [ -f "MAI-CUSTOMIZATIONS-CHECKLIST.md" ] && mv -v "MAI-CUSTOMIZATIONS-CHECKLIST.md" "docs/customization/customization-checklist.md"
    [ -f "docs/CUSTOMIZATION-EXTRACTION-PLAN.md" ] && mv -v "docs/CUSTOMIZATION-EXTRACTION-PLAN.md" "docs/customization/extraction-plan.md"
    
    # Move operations docs
    [ -f "INSTALLATION.md" ] && mv -v "INSTALLATION.md" "docs/operations/installation.md"
    [ -f "TROUBLESHOOTING.md" ] && mv -v "TROUBLESHOOTING.md" "docs/operations/troubleshooting.md"
    [ -f "docs/SECURITY.md" ] && mv -v "docs/SECURITY.md" "docs/operations/security.md"
    
    # Move configuration docs
    [ -f "docs/apache.md" ] && mv -v "docs/apache.md" "docs/configuration/apache.md"
    
    # Remove old docs README if it exists
    [ -f "docs/README.md" ] && rm -v "docs/README.md"
    
    # Clean up empty directories
    [ -d "deployments/docs" ] && [ -z "$(ls -A deployments/docs)" ] && rmdir -v "deployments/docs"
    
    echo ""
    echo "Creating documentation index..."
    
    # Create new docs index
    cat > docs/README.md << 'EOF'
# mAI Documentation

Welcome to the mAI documentation. This directory contains all documentation organized by category.

## Documentation Structure

### 📦 [Deployment](./deployment/)
- [Hetzner Deployment Guide](./deployment/hetzner-guide.md) - Step-by-step production deployment on Hetzner

### 🛠️ [Development](./development/)
- [Contributing Guide](./development/contributing.md) - How to contribute to mAI
- [Upgrade Guide](./development/upgrade-guide.md) - How to merge updates from Open WebUI
- [Development Scripts](./development/development-scripts.md) - Available development scripts

### 🎨 [Customization](./customization/)
- [mAI Changelog](./customization/mai-changelog.md) - Changes specific to mAI
- [Customization Checklist](./customization/customization-checklist.md) - Tracking customizations
- [Extraction Plan](./customization/extraction-plan.md) - Future configuration-based customization

### 🔧 [Operations](./operations/)
- [Installation Guide](./operations/installation.md) - How to install mAI
- [Troubleshooting](./operations/troubleshooting.md) - Common issues and solutions
- [Security](./operations/security.md) - Security considerations

### ⚙️ [Configuration](./configuration/)
- [Apache Configuration](./configuration/apache.md) - Apache reverse proxy setup

## Quick Links

- [Main README](../README.md) - Project overview
- [CLAUDE.md](../CLAUDE.md) - Instructions for Claude Code
- [Deployments](../deployments/README.md) - Client deployment system
EOF
    
    echo ""
    echo "Updating main README references..."
    
    # Update references in main README (this is a simplified version)
    if [ -f "README.md" ]; then
        echo "Note: You may need to manually update links in README.md to point to new documentation locations"
    fi
    
    echo ""
    echo "Documentation reorganization completed!"
    echo ""
    echo "Next steps:"
    echo "1. Review the new documentation structure in docs/"
    echo "2. Update any broken links in README.md and other files"
    echo "3. Commit the changes"
else
    echo "Reorganization cancelled."
fi