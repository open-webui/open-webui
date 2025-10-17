#!/bin/bash
# Deploy Containerized nginx for Open WebUI Multi-Tenant Setup
# This script deploys nginx as a Docker container for reverse proxying to Open WebUI instances

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
NGINX_CONTAINER_NAME="openwebui-nginx"
NETWORK_NAME="openwebui-network"
NGINX_CONFIG_DIR="/opt/openwebui-nginx"
NGINX_CONF_D="${NGINX_CONFIG_DIR}/conf.d"
NGINX_SSL_DIR="${NGINX_CONFIG_DIR}/ssl"
NGINX_LOGS_VOLUME="nginx-logs"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deploy Containerized nginx           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Check if nginx container already exists
if docker ps -a --format "{{.Names}}" | grep -q "^${NGINX_CONTAINER_NAME}$"; then
    echo -e "${YELLOW}⚠️  nginx container already exists!${NC}"
    echo
    echo "Options:"
    echo "1) Remove and redeploy"
    echo "2) Exit"
    echo
    read -p "Choose option (1-2): " option

    if [[ "$option" == "1" ]]; then
        echo "Removing existing nginx container..."
        docker stop ${NGINX_CONTAINER_NAME} 2>/dev/null || true
        docker rm ${NGINX_CONTAINER_NAME} 2>/dev/null || true
        echo -e "${GREEN}✅ Removed${NC}"
    else
        echo "Exiting..."
        exit 0
    fi
fi

# Step 1: Create custom Docker network
echo -e "${BLUE}Step 1: Create custom Docker network${NC}"
if docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
    echo -e "${GREEN}✅ Network '${NETWORK_NAME}' already exists${NC}"
else
    docker network create ${NETWORK_NAME}
    echo -e "${GREEN}✅ Created network '${NETWORK_NAME}'${NC}"
fi
echo

# Step 2: Create nginx config directory structure
echo -e "${BLUE}Step 2: Create nginx config directories${NC}"
mkdir -p ${NGINX_CONF_D}
mkdir -p ${NGINX_SSL_DIR}
mkdir -p ${NGINX_CONFIG_DIR}/webroot  # For Let's Encrypt webroot challenges
echo -e "${GREEN}✅ Created directories:${NC}"
echo "   - ${NGINX_CONF_D}"
echo "   - ${NGINX_SSL_DIR}"
echo "   - ${NGINX_CONFIG_DIR}/webroot"
echo

# Step 3: Create main nginx.conf
echo -e "${BLUE}Step 3: Create main nginx.conf${NC}"
cat > ${NGINX_CONFIG_DIR}/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_upgrade" "$http_connection" upgrade';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    # Include all site configs
    include /etc/nginx/conf.d/*.conf;
}
EOF
echo -e "${GREEN}✅ Created ${NGINX_CONFIG_DIR}/nginx.conf${NC}"
echo

# Step 4: Migrate existing nginx configs
echo -e "${BLUE}Step 4: Migrate existing nginx configs${NC}"
if [ -d "/etc/nginx/sites-available" ]; then
    echo "Found existing nginx configs in /etc/nginx/sites-available"
    echo
    echo "Do you want to convert existing configs for containerized nginx?"
    echo "(This will update proxy_pass from localhost:PORT to container:8080)"
    read -p "Convert configs? (y/N): " convert_confirm

    if [[ "$convert_confirm" =~ ^[Yy]$ ]]; then
        for config_file in /etc/nginx/sites-available/*.conf; do
            if [ -f "$config_file" ]; then
                filename=$(basename "$config_file")
                echo "  Converting: $filename"

                # Copy and convert proxy_pass
                cp "$config_file" "${NGINX_CONF_D}/${filename}"

                # Replace localhost:XXXX with container names
                # This is a basic conversion - may need manual adjustment
                echo "    ⚠️  Manual review required for: ${NGINX_CONF_D}/${filename}"
            fi
        done
        echo -e "${YELLOW}⚠️  Please review and update proxy_pass directives in ${NGINX_CONF_D}/${NC}"
        echo "    Change: proxy_pass http://localhost:808X;"
        echo "    To:     proxy_pass http://openwebui-CONTAINER-NAME:8080;"
    fi
else
    echo "No existing nginx configs found at /etc/nginx/sites-available"
fi
echo

# Step 5: Create default config (if no configs exist)
if [ -z "$(ls -A ${NGINX_CONF_D})" ]; then
    echo -e "${BLUE}Creating default nginx config...${NC}"
    cat > ${NGINX_CONF_D}/default.conf << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        return 404;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    echo -e "${GREEN}✅ Created default config${NC}"
fi
echo

# Step 6: Deploy nginx container
echo -e "${BLUE}Step 6: Deploy nginx container${NC}"

# Check if SSL certificates exist
if [ -d "/etc/letsencrypt" ]; then
    SSL_MOUNT="-v /etc/letsencrypt:/etc/letsencrypt:ro"
    echo "✅ Found Let's Encrypt certificates - mounting read-only"
else
    SSL_MOUNT=""
    echo "ℹ️  No SSL certificates found at /etc/letsencrypt"
fi

docker run -d \
    --name ${NGINX_CONTAINER_NAME} \
    --network ${NETWORK_NAME} \
    -p 80:80 \
    -p 443:443 \
    -v ${NGINX_CONFIG_DIR}/nginx.conf:/etc/nginx/nginx.conf:ro \
    -v ${NGINX_CONF_D}:/etc/nginx/conf.d:ro \
    -v ${NGINX_CONFIG_DIR}/webroot:/var/www/html \
    ${SSL_MOUNT} \
    -v ${NGINX_LOGS_VOLUME}:/var/log/nginx \
    --restart unless-stopped \
    nginx:alpine

echo -e "${GREEN}✅ nginx container deployed${NC}"
echo

# Step 7: Verify deployment
echo -e "${BLUE}Step 7: Verify deployment${NC}"
sleep 2

if docker ps --filter "name=${NGINX_CONTAINER_NAME}" --format "{{.Status}}" | grep -q "Up"; then
    echo -e "${GREEN}✅ nginx container is running${NC}"

    # Test health endpoint
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Health check failed${NC}"
    fi
else
    echo -e "${RED}❌ nginx container failed to start${NC}"
    echo "Check logs with: docker logs ${NGINX_CONTAINER_NAME}"
    exit 1
fi
echo

# Summary
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo
echo "Container: ${NGINX_CONTAINER_NAME}"
echo "Network: ${NETWORK_NAME}"
echo "Config directory: ${NGINX_CONFIG_DIR}"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Connect Open WebUI containers to ${NETWORK_NAME}:"
echo "   docker network connect ${NETWORK_NAME} openwebui-CONTAINER-NAME"
echo
echo "2. Update nginx configs in ${NGINX_CONF_D} to use container names:"
echo "   proxy_pass http://openwebui-CONTAINER-NAME:8080;"
echo
echo "3. Reload nginx config:"
echo "   docker exec ${NGINX_CONTAINER_NAME} nginx -s reload"
echo
echo "4. Test configuration:"
echo "   docker exec ${NGINX_CONTAINER_NAME} nginx -t"
echo
echo "5. View logs:"
echo "   docker logs -f ${NGINX_CONTAINER_NAME}"
echo
echo -e "${BLUE}For SSL certificates:${NC}"
echo "  Keep using host certbot with renewal hooks, or"
echo "  Use certbot container (see documentation)"
echo
