#!/bin/bash
# Convert nginx Configs for Containerized nginx
# This script converts proxy_pass directives from localhost:PORT to container:8080

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SOURCE_DIR="${1:-/etc/nginx/sites-available}"
DEST_DIR="${2:-/opt/openwebui-nginx/conf.d}"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Convert nginx Configs                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}❌ Source directory not found: $SOURCE_DIR${NC}"
    exit 1
fi

if [ ! -d "$DEST_DIR" ]; then
    echo "Creating destination directory: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

# Function to extract container name from config
extract_container_name() {
    local config_file="$1"
    local server_name=$(grep -m 1 "server_name" "$config_file" | awk '{print $2}' | sed 's/;//')

    if [[ -z "$server_name" ]]; then
        echo ""
        return
    fi

    # Convert FQDN to container name format
    # Example: chat.quantabase.io -> openwebui-chat-quantabase-io
    local sanitized=$(echo "$server_name" | sed 's/\./-/g' | sed 's/:/-/g')
    echo "openwebui-${sanitized}"
}

# Function to extract port from localhost proxy_pass
extract_port() {
    local config_file="$1"
    grep -m 1 "proxy_pass.*localhost:" "$config_file" | grep -o 'localhost:[0-9]*' | cut -d: -f2
}

# Convert each config file
echo "Converting configs from $SOURCE_DIR to $DEST_DIR"
echo

for config_file in "$SOURCE_DIR"/*.conf; do
    if [ ! -f "$config_file" ]; then
        continue
    fi

    filename=$(basename "$config_file")
    dest_file="${DEST_DIR}/${filename}"

    echo "Processing: $filename"

    # Extract info
    port=$(extract_port "$config_file")
    container_name=$(extract_container_name "$config_file")

    if [[ -z "$port" ]]; then
        echo -e "  ${YELLOW}⚠️  No localhost:PORT found - copying as-is${NC}"
        cp "$config_file" "$dest_file"
        continue
    fi

    if [[ -z "$container_name" ]]; then
        echo -e "  ${YELLOW}⚠️  Could not determine container name - copying as-is${NC}"
        cp "$config_file" "$dest_file"
        continue
    fi

    # Convert proxy_pass
    echo "  localhost:$port → $container_name:8080"
    sed "s|proxy_pass http://localhost:${port}|proxy_pass http://${container_name}:8080|g" \
        "$config_file" > "$dest_file"

    # Also update comments if they mention localhost
    sed -i "s|localhost:${port}|${container_name}:8080|g" "$dest_file"

    echo -e "  ${GREEN}✅ Converted${NC}"
done

echo
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Conversion Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo
echo "Converted configs saved to: $DEST_DIR"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review converted configs: ls -la $DEST_DIR"
echo "2. Test nginx configuration: docker exec openwebui-nginx nginx -t"
echo "3. Reload nginx: docker exec openwebui-nginx nginx -s reload"
echo
