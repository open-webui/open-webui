#!/bin/bash
# Deploy nginx container as part of golden image
# Called by Packer during image build

set -euo pipefail

echo "=== Deploying nginx container ==="

# Configuration
NGINX_CONTAINER_NAME="openwebui-nginx"
NETWORK_NAME="openwebui-network"
NGINX_CONFIG_DIR="/opt/openwebui-nginx"

# Create custom Docker network
echo "Creating Docker network: $NETWORK_NAME"
if docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
    echo "Network already exists"
else
    docker network create ${NETWORK_NAME}
    echo "Network created"
fi

# Create nginx config directory structure
echo "Creating nginx config directories"
mkdir -p ${NGINX_CONFIG_DIR}/{conf.d,ssl,webroot}
chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${NGINX_CONFIG_DIR}

# Create main nginx.conf
echo "Creating main nginx.conf"
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
                    '"$http_user_agent" "$http_x_forwarded_for"';

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

# Create default config (health check only)
echo "Creating default nginx config"
cat > ${NGINX_CONFIG_DIR}/conf.d/default.conf << 'EOF'
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

# Create nginx logs volume
echo "Creating nginx logs volume"
docker volume create nginx-logs

# Pull nginx image
echo "Pulling nginx:alpine image"
docker pull nginx:alpine

# Deploy nginx container
echo "Deploying nginx container"
docker run -d \
    --name ${NGINX_CONTAINER_NAME} \
    --network ${NETWORK_NAME} \
    -p 80:80 \
    -p 443:443 \
    -v ${NGINX_CONFIG_DIR}/nginx.conf:/etc/nginx/nginx.conf:ro \
    -v ${NGINX_CONFIG_DIR}/conf.d:/etc/nginx/conf.d:ro \
    -v ${NGINX_CONFIG_DIR}/webroot:/var/www/html \
    -v nginx-logs:/var/log/nginx \
    --restart unless-stopped \
    nginx:alpine

# Wait for nginx to start
echo "Waiting for nginx to start..."
sleep 3

# Verify nginx is running
if docker ps --filter "name=${NGINX_CONTAINER_NAME}" | grep -q ${NGINX_CONTAINER_NAME}; then
    echo "nginx container deployed successfully"

    # Test health endpoint
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        echo "Health check passed"
    else
        echo "WARNING: Health check failed"
    fi
else
    echo "ERROR: nginx container failed to start"
    docker logs ${NGINX_CONTAINER_NAME}
    exit 1
fi

echo "=== nginx deployment complete ==="
