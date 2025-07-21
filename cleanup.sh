#!/bin/bash
# mAI Repository Cleanup Script
# This script removes unnecessary files identified during repository analysis

echo "mAI Repository Cleanup"
echo "====================="
echo ""
echo "This script will remove the following unnecessary files:"
echo "- fix_polish_translation.py (one-time migration script)"
echo "- contribution_stats.py (utility script)"
echo "- test-mai-container.sh (test script)"
echo "- package.json.backup-* (backup file)"
echo "- deployments/scripts/ (empty directory)"
echo ""
read -p "Do you want to proceed? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing files..."
    
    # Remove individual files
    [ -f "fix_polish_translation.py" ] && rm -v "fix_polish_translation.py"
    [ -f "contribution_stats.py" ] && rm -v "contribution_stats.py"
    [ -f "test-mai-container.sh" ] && rm -v "test-mai-container.sh"
    
    # Remove backup files
    rm -v package.json.backup-* 2>/dev/null || true
    
    # Remove empty directory
    [ -d "deployments/scripts" ] && [ -z "$(ls -A deployments/scripts)" ] && rmdir -v "deployments/scripts"
    
    echo ""
    echo "Cleanup completed!"
else
    echo "Cleanup cancelled."
fi