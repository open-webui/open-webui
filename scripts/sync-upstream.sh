#!/bin/bash
# Safe synchronization with upstream

set -e

echo "🔄 Starting upstream sync..."

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Fetch upstream
echo "📥 Fetching upstream..."
git fetch upstream

# Create backup branch
BACKUP_BRANCH="backup-$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BACKUP_BRANCH"
echo "✅ Created backup branch: $BACKUP_BRANCH"

# Switch to main
git checkout main

# Attempt merge
echo "🔀 Attempting merge with upstream/main..."
if git merge upstream/main --no-edit; then
    echo "✅ Merge successful!"
else
    echo "❌ Merge conflicts detected!"
    echo "Please resolve conflicts manually, then run:"
    echo "  git add ."
    echo "  git commit"
    exit 1
fi

# Check patches
echo "🩹 Checking patches..."
FAILED_PATCHES=()
for patch in patches/*.patch; do
    if [ -f "$patch" ]; then
        echo -n "Checking $(basename "$patch")... "
        if git apply --check "$patch" 2>/dev/null; then
            echo "✅"
        else
            echo "❌"
            FAILED_PATCHES+=("$patch")
        fi
    fi
done

if [ ${#FAILED_PATCHES[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  The following patches need to be updated:"
    for patch in "${FAILED_PATCHES[@]}"; do
        echo "  - $patch"
    done
    echo ""
    echo "To fix a patch:"
    echo "1. Apply changes manually"
    echo "2. Create new patch with: ./scripts/create-patch.sh"
    echo "3. Replace old patch file"
fi

echo ""
echo "📊 Sync summary:"
echo "  - Current branch: $(git branch --show-current)"
echo "  - Latest upstream: $(git log upstream/main -1 --pretty=format:'%h - %s')"
echo "  - Backup branch: $BACKUP_BRANCH"

# Create tag for version
if [ ${#FAILED_PATCHES[@]} -eq 0 ]; then
    TAG="sync-$(date +%Y%m%d)"
    git tag -a "$TAG" -m "Synced with upstream on $(date)"
    echo "  - Created tag: $TAG"
fi