#!/bin/bash
# Script for creating patches from your changes

set -e

PATCH_DIR="patches"
PATCH_NUMBER=$(ls -1 $PATCH_DIR/*.patch 2>/dev/null | wc -l | xargs printf "%03d")
PATCH_NUMBER=$((PATCH_NUMBER + 1))

echo "Creating patch #$PATCH_NUMBER"
echo -n "Enter patch name (e.g., branding, auth-fix): "
read PATCH_NAME

echo -n "Enter patch description: "
read PATCH_DESC

# Create patch
git diff --staged > "$PATCH_DIR/${PATCH_NUMBER}-${PATCH_NAME}.patch"

# Add metadata
cat > "$PATCH_DIR/${PATCH_NUMBER}-${PATCH_NAME}.json" <<EOF
{
  "number": "$PATCH_NUMBER",
  "name": "$PATCH_NAME",
  "description": "$PATCH_DESC",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "author": "$(git config user.name)",
  "base_commit": "$(git rev-parse HEAD)"
}
EOF

echo "Patch created: $PATCH_DIR/${PATCH_NUMBER}-${PATCH_NAME}.patch"
echo "Remember to test the patch with: git apply --check $PATCH_DIR/${PATCH_NUMBER}-${PATCH_NAME}.patch"