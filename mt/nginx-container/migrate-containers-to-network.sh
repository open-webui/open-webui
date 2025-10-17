#!/bin/bash
# Migrate Open WebUI Containers to Custom Network
# This script connects existing Open WebUI containers to the openwebui-network
# and optionally removes port mappings (ports only needed for host nginx)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
NETWORK_NAME="openwebui-network"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Migrate Containers to Network       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Check if network exists
if ! docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
    echo -e "${RED}❌ Network '${NETWORK_NAME}' does not exist${NC}"
    echo "Create it first with: docker network create ${NETWORK_NAME}"
    exit 1
fi

# Find all Open WebUI containers (exclude sync nodes)
containers=($(docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | grep -v "sync-node"))

if [ ${#containers[@]} -eq 0 ]; then
    echo "No Open WebUI containers found."
    exit 0
fi

echo "Found ${#containers[@]} Open WebUI container(s):"
for container in "${containers[@]}"; do
    status=$(docker ps -a --filter "name=$container" --format "{{.Status}}")
    echo "  - $container ($status)"
done
echo

echo -e "${YELLOW}Migration Options:${NC}"
echo "1) Connect to network (keep existing port mappings)"
echo "2) Recreate without port mappings (requires nginx container)"
echo "3) Exit"
echo
read -p "Choose option (1-3): " option

case "$option" in
    1)
        echo
        echo -e "${BLUE}Connecting containers to ${NETWORK_NAME}...${NC}"
        for container in "${containers[@]}"; do
            echo
            echo "Processing: $container"

            # Check if already connected
            if docker inspect "$container" --format '{{range $net,$v := .NetworkSettings.Networks}}{{$net}}{{end}}' | grep -q "${NETWORK_NAME}"; then
                echo -e "  ${GREEN}✅ Already connected to ${NETWORK_NAME}${NC}"
            else
                # Connect to network
                docker network connect ${NETWORK_NAME} "$container"
                echo -e "  ${GREEN}✅ Connected to ${NETWORK_NAME}${NC}"

                # Optionally disconnect from bridge
                read -p "  Disconnect from default bridge network? (y/N): " disconnect
                if [[ "$disconnect" =~ ^[Yy]$ ]]; then
                    docker network disconnect bridge "$container" 2>/dev/null || echo "  ℹ️  Not connected to bridge"
                fi
            fi
        done
        ;;

    2)
        echo
        echo -e "${RED}⚠️  WARNING: This will recreate containers!${NC}"
        echo "This approach:"
        echo "  - Stops and removes existing containers"
        echo "  - Recreates them on ${NETWORK_NAME} without port mappings"
        echo "  - Preserves data volumes"
        echo "  - Requires nginx container to be running"
        echo
        read -p "Are you sure? (yes/no): " confirm

        if [[ "$confirm" != "yes" ]]; then
            echo "Cancelled"
            exit 0
        fi

        # Check if nginx container is running
        if ! docker ps --filter "name=openwebui-nginx" --format "{{.Names}}" | grep -q "openwebui-nginx"; then
            echo -e "${RED}❌ nginx container is not running${NC}"
            echo "Deploy it first with: ./deploy-nginx-container.sh"
            exit 1
        fi

        for container in "${containers[@]}"; do
            echo
            echo -e "${BLUE}Recreating: $container${NC}"

            # Get container configuration
            echo "  Extracting configuration..."
            container_config=$(docker inspect "$container")

            # Extract critical environment variables
            env_vars=$(echo "$container_config" | jq -r '.[0].Config.Env[]' | grep -E '^(GOOGLE_|OAUTH_|WEBUI_|FQDN|CLIENT_NAME|ENABLE_|OPENID_|USER_|DATABASE_)' | sed 's/^/-e /')

            # Extract volumes
            volumes=$(echo "$container_config" | jq -r '.[0].Mounts[] | select(.Type=="volume") | "-v \(.Name):\(.Destination)"')

            # Get image
            image=$(echo "$container_config" | jq -r '.[0].Config.Image')

            # Stop and remove old container
            echo "  Stopping container..."
            docker stop "$container"
            echo "  Removing container..."
            docker rm "$container"

            # Recreate without port mappings
            echo "  Creating new container on ${NETWORK_NAME}..."
            eval docker run -d \
                --name "$container" \
                --network ${NETWORK_NAME} \
                $env_vars \
                $volumes \
                --restart unless-stopped \
                "$image"

            echo -e "  ${GREEN}✅ Recreated successfully${NC}"
        done
        ;;

    3)
        echo "Exiting..."
        exit 0
        ;;

    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Migration Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo
echo "Verify connectivity:"
echo "  docker exec ${containers[0]} ping -c 1 openwebui-nginx"
echo
echo "View network members:"
echo "  docker network inspect ${NETWORK_NAME}"
echo
