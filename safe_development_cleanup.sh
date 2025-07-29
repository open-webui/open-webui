#!/bin/bash

# Safe Development Cleanup Script
# Removes only completed/obsolete files while preserving all development tools
# and docker-compose configurations

echo "🧹 mAI Safe Development Cleanup"
echo "==============================="
echo ""

# Counter for tracking
deleted=0
not_found=0

# Function to safely remove file
safe_remove() {
    local file="$1"
    if [ -f "$file" ]; then
        rm -f "$file"
        if [ $? -eq 0 ]; then
            echo "✅ Deleted: $file"
            ((deleted++))
        else
            echo "❌ Failed to delete: $file"
        fi
    else
        echo "⏭️  Not found (already deleted?): $file"
        ((not_found++))
    fi
}

# Function to safely remove directory
safe_remove_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        if [ $? -eq 0 ]; then
            echo "✅ Deleted directory: $dir"
            ((deleted++))
        else
            echo "❌ Failed to delete directory: $dir"
        fi
    else
        echo "⏭️  Directory not found: $dir"
        ((not_found++))
    fi
}

echo "🗂️  Removing completed test/debug files..."
echo "----------------------------------------"

# Completed one-time test scripts
safe_remove "test_data_loss_fix.py"
safe_remove "test_bulk_sync_fix.py"
safe_remove "test_streaming_usage_capture.py"
safe_remove "backend/validate_usage_tracking_fix.py"
safe_remove "backend/investigate_and_clean_database.py"

echo ""
echo "📊 Removing historical debug reports..."
echo "---------------------------------------"

# JSON debug reports from completed investigations
safe_remove "backend/container_debug_results.json"
safe_remove "backend/database_investigation_20250729_133128.json"
safe_remove "backend/live_environment_debug_results.json"
safe_remove "backend/usage_capture_failure_report.json"
safe_remove "backend/usage_tracking_validation_report.json"

echo ""
echo "📝 Removing old log files..."
echo "-----------------------------"

# Log files that can be regenerated
safe_remove "backend.log"
safe_remove "backend/debug_usage_capture.log"

echo ""
echo "📚 Removing completed refactoring documentation..."
echo "--------------------------------------------------"

# Completed refactoring docs
safe_remove "refactoring_summary.md"
safe_remove "backend/REFACTORING_SUCCESS_REPORT.md"
safe_remove "backend/REFACTORING_SAFETY_ANALYSIS.md"

echo ""
echo "🗄️  Removing legacy code files..."
echo "----------------------------------"

# Legacy code that has been replaced
safe_remove "backend/open_webui/utils/openrouter_models_old.py"
safe_remove "backend/open_webui/utils/daily_batch_processor_legacy.py"
safe_remove "backend/open_webui/utils/enhanced_usage_calculation_legacy.py"

echo ""
echo "🛠️  Removing one-time cleanup scripts..."
echo "----------------------------------------"

# Scripts that completed their purpose
safe_remove "cleanup_legacy_files.sh"
safe_remove "safe_cleanup.sh"

echo ""
echo "🗑️  Removing cache and compiled files..."
echo "----------------------------------------"

# Find and remove __pycache__ directories
echo "Removing Python cache directories..."
find . -type d -name "__pycache__" -not -path "./node_modules/*" -not -path "./venv/*" -not -path "./backend/venv/*" | while read dir; do
    safe_remove_dir "$dir"
done

# Remove .pyc files
echo "Removing compiled Python files..."
find . -name "*.pyc" -not -path "./node_modules/*" -not -path "./venv/*" -not -path "./backend/venv/*" | while read file; do
    safe_remove "$file"
done

# Remove cache directory contents (but keep the directory structure)
if [ -d "backend/data/cache" ]; then
    echo "Cleaning cache directory contents..."
    rm -rf backend/data/cache/* 2>/dev/null || true
    echo "✅ Cleaned: backend/data/cache/ contents"
fi

echo ""
echo "📊 Cleanup Summary:"
echo "==================="
echo "   - Files deleted: $deleted"
echo "   - Files not found: $not_found"
echo ""

echo "✅ PRESERVED (as requested):"
echo "   - All docker-compose*.yaml files"
echo "   - All development tools and scripts"
echo "   - All documentation in docs/"
echo "   - All current debugging tools"
echo "   - All testing infrastructure"
echo "   - All environment configs"
echo ""

echo "🎉 Safe cleanup complete!"
echo ""
echo "💡 Note: Only obsolete files from completed work were removed."
echo "   Your development environment remains fully intact."