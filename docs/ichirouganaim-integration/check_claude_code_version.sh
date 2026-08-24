#!/usr/bin/env bash
# Reports whether a newer @anthropic-ai/claude-code version exists on npm
# than the one pinned in Dockerfile.claude-cli -- informational only,
# never modifies anything and never bumps the pin itself. The pin is
# deliberate (decisions.md: an unpinned "latest" once silently swallowed
# an out-of-disk-space error instead of reporting it), so auto-bumping
# defeats the point -- this just surfaces that a newer version exists so a
# human can decide whether to test and adopt it, on their own schedule,
# not on this script's.
#
# Usage: run from the repo root.
#   ./docs/ichirouganaim-integration/check_claude_code_version.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCKERFILE="$REPO_ROOT/Dockerfile.claude-cli"

if [ ! -f "$DOCKERFILE" ]; then
  echo "Error: $DOCKERFILE not found." >&2
  exit 1
fi

PINNED="$(grep -oE '@anthropic-ai/claude-code@[0-9.]+' "$DOCKERFILE" | head -1 | cut -d@ -f3)"
if [ -z "$PINNED" ]; then
  echo "Error: couldn't find a pinned @anthropic-ai/claude-code@X.Y.Z version in $DOCKERFILE." >&2
  exit 1
fi

LATEST="$(npm view @anthropic-ai/claude-code version 2>/dev/null || echo "")"
if [ -z "$LATEST" ]; then
  echo "Error: couldn't reach npm to check the latest version (offline?)." >&2
  exit 1
fi

echo "Pinned in Dockerfile.claude-cli: $PINNED"
echo "Latest on npm:                  $LATEST"

if [ "$PINNED" != "$LATEST" ]; then
  echo
  echo "A newer version is available. To adopt it (after testing):"
  echo "  1. Edit Dockerfile.claude-cli's 'npm install -g @anthropic-ai/claude-code@$PINNED' line to @$LATEST"
  echo "  2. docker compose -f docker-compose.yaml -f docker-compose.override.yaml build && ... up -d"
  echo "  3. Re-verify a real chat + tool call still works (SETUP.md step 9)"
else
  echo
  echo "Up to date."
fi
