#!/bin/bash

# Script to remove legacy backup files from the usage tracking refactoring
# These files contain references to unused fields that have been removed

echo "🧹 Cleaning up legacy usage tracking files..."
echo ""

# Files to remove
FILES_TO_DELETE=(
    "backend/open_webui/routers/usage_tracking_BACKUP_20250727_225652.py"
    "backend/open_webui/routers/usage_tracking_ORIGINAL_MONOLITHIC.py"
    "src/lib/components/admin/Settings/MyOrganizationUsage.svelte.original"
    "test_monthly_summary_refactor.py"
)

# Counter for tracking
deleted=0
not_found=0

# Remove each file
for file in "${FILES_TO_DELETE[@]}"; do
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
done

echo ""
echo "📊 Summary:"
echo "   - Files deleted: $deleted"
echo "   - Files not found: $not_found"
echo ""

# Optional: Find and list any other backup files
echo "🔍 Checking for other backup files..."
OTHER_BACKUPS=$(find . -name "*BACKUP*" -o -name "*ORIGINAL*" -o -name "*.original" 2>/dev/null | grep -v node_modules | grep -v .git)

if [ -n "$OTHER_BACKUPS" ]; then
    echo "⚠️  Found other backup files that might need attention:"
    echo "$OTHER_BACKUPS" | while read -r file; do
        echo "   - $file"
    done
else
    echo "✅ No other backup files found."
fi

echo ""
echo "✨ Cleanup complete!"