#!/bin/bash

# Cleanup script for removing testing and debugging scripts from backup folder
# Target: /Users/patpil/Documents/Projects/mAI/customization-backup/current-solution-20250725-151312/scripts

BACKUP_SCRIPTS_DIR="/Users/patpil/Documents/Projects/mAI/customization-backup/current-solution-20250725-151312/scripts"

echo "🧹 Cleaning up testing and debugging scripts from backup folder"
echo "Target directory: $BACKUP_SCRIPTS_DIR"
echo ""

# Check if directory exists
if [ ! -d "$BACKUP_SCRIPTS_DIR" ]; then
    echo "❌ Directory not found: $BACKUP_SCRIPTS_DIR"
    exit 1
fi

echo "📂 Current directory contents:"
ls -la "$BACKUP_SCRIPTS_DIR"
echo ""

echo "🗑️  Deleting testing and debugging scripts:"

# Delete debug scripts
echo "  Removing debug_*.py scripts..."
rm -f "$BACKUP_SCRIPTS_DIR/debug_create_client.py"
rm -f "$BACKUP_SCRIPTS_DIR/debug_docker_sync.py"
rm -f "$BACKUP_SCRIPTS_DIR/debug_mapping_issue.py"
rm -f "$BACKUP_SCRIPTS_DIR/debug_openrouter_api.py"

# Delete test scripts
echo "  Removing test_*.py scripts..."
rm -f "$BACKUP_SCRIPTS_DIR/test_auto_mapping.py"
rm -f "$BACKUP_SCRIPTS_DIR/test_automatic_mapping.py"
rm -f "$BACKUP_SCRIPTS_DIR/test_docker_sync.py"
rm -f "$BACKUP_SCRIPTS_DIR/test_docker_sync_correct.py"
rm -f "$BACKUP_SCRIPTS_DIR/test_new_api_key.py"
rm -f "$BACKUP_SCRIPTS_DIR/test_sync_function.py"

# Delete other testing/debugging files
echo "  Removing other test/debug files..."
rm -f "$BACKUP_SCRIPTS_DIR/simple_test_mapping.py"
rm -f "$BACKUP_SCRIPTS_DIR/validate_openrouter_api.py"
rm -f "$BACKUP_SCRIPTS_DIR/setup_test_client_org.py"

# Delete fix scripts (they were for specific debugging issues)
echo "  Removing fix_*.py scripts..."
rm -f "$BACKUP_SCRIPTS_DIR/fix_api_key_mapping.py"
rm -f "$BACKUP_SCRIPTS_DIR/fix_database_schema.py"

# Delete openrouter debug folder contents
echo "  Removing openrouter debug scripts..."
rm -f "$BACKUP_SCRIPTS_DIR/openrouter/fix_openrouter_docker.py"
rm -f "$BACKUP_SCRIPTS_DIR/openrouter/production_fix.py"
rm -f "$BACKUP_SCRIPTS_DIR/openrouter/verify_config.py"

# Keep manage_models.py as it might be useful for production
# rm -f "$BACKUP_SCRIPTS_DIR/openrouter/manage_models.py"

# Delete documentation that's specific to debugging
echo "  Removing debug documentation..."
rm -f "$BACKUP_SCRIPTS_DIR/VALIDATION_GUIDE.md"

# Delete example/workflow files (documentation purposes only)
echo "  Removing example/workflow documentation..."
rm -f "$BACKUP_SCRIPTS_DIR/workflow_example.md"

echo ""
echo "✅ Cleanup completed!"
echo ""

echo "📂 Remaining files in directory:"
ls -la "$BACKUP_SCRIPTS_DIR"
echo ""

echo "📋 Summary of files kept (production-relevant):"
echo "  ✅ README_refined.md - Documentation for client key generation"
echo "  ✅ db_backup.sh - Database backup utility"
echo "  ✅ db_monitor.py - Database monitoring"
echo "  ✅ keygen.py - Client API key generator"
echo "  ✅ simple_create_client_key.py - Simplified key creation"
echo "  ✅ standalone_create_client_key.py - Standalone key creation"
echo "  ✅ prepare-pyodide.js - Frontend preparation"
echo "  ✅ update-from-upstream.sh - Update utility"
echo "  ✅ openrouter/manage_models.py - Model management utility"
echo ""

echo "🎯 All testing and debugging scripts have been removed!"
echo "   Only production-relevant scripts and documentation remain."