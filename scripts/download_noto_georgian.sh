#!/usr/bin/env bash
set -euo pipefail

# Attempt to download Noto Sans Georgian TTF into scripts/fonts/
OUT_DIR="$(dirname "$0")/fonts"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/NotoSansGeorgian-Bold.ttf"

echo "Attempting to download Noto Sans Georgian into $OUT_FILE"

# Candidate URLs (raw GitHub paths). If these fail, please download manually and commit the TTF.
URLS=(
  "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansGeorgian/NotoSansGeorgian-Bold.ttf"
  "https://github.com/google/fonts/raw/main/ofl/notosansgeorgian/NotoSansGeorgian-Bold.ttf"
  "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansGeorgian/NotoSansGeorgian-Regular.ttf"
  "https://github.com/google/fonts/raw/main/ofl/notosansgeorgian/NotoSansGeorgian-Regular.ttf"
)

for url in "${URLS[@]}"; do
  echo "Trying $url"
  if command -v curl >/dev/null 2>&1; then
    if curl -fsSL "$url" -o "$OUT_FILE"; then
      echo "Downloaded to $OUT_FILE"
      exit 0
    fi
  elif command -v wget >/dev/null 2>&1; then
    if wget -qO "$OUT_FILE" "$url"; then
      echo "Downloaded to $OUT_FILE"
      exit 0
    fi
  fi
done

echo "Download failed. Please manually download NotoSansGeorgian-Regular.ttf and place it in $OUT_DIR or commit it to the repo." >&2
exit 1
