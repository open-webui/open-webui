#!/bin/bash
set -e

echo "🔥 FixCraft AI WebUI Customizer — Launching..."
echo "Dranding Customizer By F1xGOD"
echo ""
# 1️⃣ Ask for local repo path
read -p "👉 Path to your local open-webui directory (default: current dir): " OPENWEBUI_DIR
OPENWEBUI_DIR=${OPENWEBUI_DIR:-.}

if [[ ! -d "$OPENWEBUI_DIR" ]]; then
  echo "❌ Directory '$OPENWEBUI_DIR' not found! Exiting."
  exit 1
fi

cd "$OPENWEBUI_DIR"
echo "🚀 Operating in: $(pwd)"

# 2️⃣ Get new name & asset URL
read -p "👉 New WebUI name (default: FixCraft AI): " NEW_NAME
NEW_NAME=${NEW_NAME:-FixCraft AI}

read -p "👉 Base URL for assets (e.g. https://www.fixcraft.org): " BASE_URL
if [[ -z "$BASE_URL" ]]; then
  echo "❌ No URL given. Exiting."
  exit 1
fi

echo -e "\n🔍 Checking assets at $BASE_URL..."
declare -A ASSETS=(
  ["favicon.png"]="500x500"
  ["logo.png"]="500x500"
  ["web-app-manifest-512x512.png"]="512x512"
  ["web-app-manifest-192x192.png"]="192x192"
  ["favicon-96x96.png"]="96x96"
  ["apple-touch-icon.png"]="180x180"
  ["favicon.svg"]="vector"
  ["favicon.ico"]="16x16/32x32"
  ["splash.png"]="any"
  ["splash-dark.png"]="any"
)

MISSING=()
for file in "${!ASSETS[@]}"; do
  if ! curl -sSf "$BASE_URL/$file" -o /dev/null; then
    echo "❌ Missing: $file (should be ${ASSETS[$file]})"
    MISSING+=("$file (${ASSETS[$file]})")
  else
    echo "✅ Found:   $file (${ASSETS[$file]})"
  fi
done

if (( ${#MISSING[@]} > 0 )); then
  echo -e "\n🚨 NOT ALL ASSETS INSTALLED! Fix these before running again."
  for m in "${MISSING[@]}"; do echo "   • $m"; done
  exit 1
fi

echo -e "\n✅ All assets present. Starting customization..."

# 3️⃣ Branding in HTML
sed -i "s/Open WebUI/$NEW_NAME/g" ./src/app.html

# 4️⃣ Download assets
STATIC_DIR="./backend/open_webui/static"
mkdir -p "$STATIC_DIR"
for file in "${!ASSETS[@]}"; do
  echo "⬇️  Downloading $file..."
  curl -sSf "$BASE_URL/$file" -o "$STATIC_DIR/$file"
done

# Copy favicon.png also to root static (legacy)
cp "$STATIC_DIR/favicon.png" "$STATIC_DIR/../favicon.png"

# 5️⃣ Patch env.py
ENV_PY="./backend/open_webui/env.py"
sed -i "s|WEBUI_NAME = os.environ.get.*|WEBUI_NAME = os.environ.get(\"WEBUI_NAME\", \"$NEW_NAME\")|" "$ENV_PY"
sed -i "s|WEBUI_FAVICON_URL = .*|WEBUI_FAVICON_URL = \"$BASE_URL/favicon.png\"|" "$ENV_PY"
sed -i '/if WEBUI_NAME != .*Open WebUI/,/WEBUI_NAME += .*Open WebUI/d' "$ENV_PY"

echo -e "\n🎉 DONE — '$NEW_NAME' is now baked into your local Open WebUI clone!"

