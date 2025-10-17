# Containerized nginx for Open WebUI Multi-Tenant Setup

This directory contains tools and scripts for deploying nginx as a Docker container to serve as a reverse proxy for multiple Open WebUI instances.

## Overview

**Why Containerized nginx?**
- **Isolation**: nginx runs in its own container, separate from the host system
- **Portability**: Easy to move the entire setup between servers
- **Container-to-Container Communication**: Direct networking between nginx and Open WebUI containers without exposing ports to the host
- **Simplified Management**: All configuration in one directory structure
- **Docker Network Benefits**: Automatic DNS resolution, network isolation, and service discovery

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Host System                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           openwebui-network (Custom Bridge)            │ │
│  │                                                         │ │
│  │  ┌──────────────────┐      ┌──────────────────┐       │ │
│  │  │  openwebui-nginx │      │  openwebui-chat- │       │ │
│  │  │                  │─────▶│  quantabase-io   │       │ │
│  │  │  :80, :443       │      │  :8080           │       │ │
│  │  └──────────────────┘      └──────────────────┘       │ │
│  │                                                         │ │
│  │                            ┌──────────────────┐       │ │
│  │                            │  openwebui-docs- │       │ │
│  │                            │  example-com     │       │ │
│  │                            │  :8080           │       │ │
│  │                            └──────────────────┘       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Port Mappings:                                              │
│  - 80:80   (HTTP)  → openwebui-nginx                        │
│  - 443:443 (HTTPS) → openwebui-nginx                        │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **openwebui-nginx**: Main nginx reverse proxy container
- **openwebui-network**: Custom Docker bridge network for inter-container communication
- **Open WebUI Containers**: Named using FQDN pattern (`openwebui-DOMAIN-WITH-DASHES`)
- **Configuration**: Mounted from `/opt/openwebui-nginx/` on host

## Directory Structure

```
mt/nginx-container/
├── README.md                           # This file
├── deploy-nginx-container.sh           # Main deployment script
├── migrate-containers-to-network.sh    # Migrate Open WebUI containers to custom network
├── convert-nginx-configs.sh            # Convert existing configs to container format
└── ../nginx-template-containerized.conf # nginx config template for containers
```

## Prerequisites

Before deploying containerized nginx:

- [ ] Docker installed and running
- [ ] Root or sudo access
- [ ] Existing Open WebUI containers (optional - can deploy nginx first)
- [ ] Domain names configured and pointing to server
- [ ] SSL certificates (if using HTTPS immediately)
- [ ] Ports 80 and 443 available on host

**Check Port Availability:**
```bash
# Check if ports are in use
sudo netstat -tlnp | grep -E ':80|:443'

# If host nginx is running, you'll need to stop it first
sudo systemctl status nginx
```

## Deployment Options

### Option 1: Fresh Deployment (Recommended for New Setups)

Deploy nginx container first, then create Open WebUI containers on the custom network.

**Advantages:**
- Clean setup from the start
- No migration needed
- Open WebUI containers don't need port mappings

**Steps:**
1. Deploy nginx container
2. Create Open WebUI containers with `--network openwebui-network` (no `-p` flags needed)
3. Configure nginx and SSL

### Option 2: Migration from Host nginx

Migrate existing setup where nginx runs on host and Open WebUI containers have port mappings.

**Advantages:**
- Preserves existing setup
- Can test before full migration
- Gradual transition possible

**Steps:**
1. Deploy nginx container
2. Migrate Open WebUI containers to custom network
3. Convert nginx configs
4. Test connectivity
5. Stop host nginx

## Quick Start

### 1. Deploy nginx Container

```bash
cd /path/to/open-webui/mt/nginx-container
sudo ./deploy-nginx-container.sh
```

**What This Does:**
- Creates `openwebui-network` custom bridge network
- Creates directory structure at `/opt/openwebui-nginx/`
- Generates main `nginx.conf`
- Deploys `openwebui-nginx` container
- Mounts SSL certificates if available at `/etc/letsencrypt/`
- Creates health check endpoint at `/health`

**Expected Output:**
```
╔════════════════════════════════════════╗
║   Deploy Containerized nginx           ║
╚════════════════════════════════════════╝

Step 1: Create custom Docker network
✅ Created network 'openwebui-network'

Step 2: Create nginx config directories
✅ Created directories:
   - /opt/openwebui-nginx/conf.d
   - /opt/openwebui-nginx/ssl
   - /opt/openwebui-nginx/webroot

Step 3: Create main nginx.conf
✅ Created /opt/openwebui-nginx/nginx.conf

Step 4: Migrate existing nginx configs
No existing nginx configs found at /etc/nginx/sites-available

Step 5: Deploy nginx container
✅ nginx container deployed

Step 6: Verify deployment
✅ nginx container is running
✅ Health check passed
```

### 2. Connect Open WebUI Containers to Network

**For New Containers:**
Use `client-manager.sh` which auto-detects containerized nginx:

```bash
cd /path/to/open-webui/mt
./client-manager.sh
# Choose "Deploy new client"
# Script will auto-detect nginx container and generate appropriate config
```

**For Existing Containers:**
Use the migration script:

```bash
sudo ./migrate-containers-to-network.sh
```

**Migration Options:**
1. **Option 1 - Keep Port Mappings**: Adds containers to custom network while preserving existing port mappings (safer, allows rollback)
2. **Option 2 - Recreate Without Ports**: Removes containers and recreates them on custom network only (more secure, nginx-only access)

### 3. Configure nginx for Each Client

**Method 1: Using client-manager.sh (Recommended)**

The `client-manager.sh` script auto-detects containerized nginx and generates appropriate configs:

```bash
cd /path/to/open-webui/mt
./client-manager.sh
# Choose option 5: "Generate nginx config for existing client"
# Script will create config in /tmp/ with setup instructions
```

**Method 2: Manual Configuration**

Create nginx config file:

```nginx
# /opt/openwebui-nginx/conf.d/chat.quantabase.io.conf

server {
    listen 80;
    listen [::]:80;
    server_name chat.quantabase.io;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name chat.quantabase.io;

    ssl_certificate /etc/letsencrypt/live/chat.quantabase.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.quantabase.io/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        # Use container name instead of localhost:PORT
        proxy_pass http://openwebui-chat-quantabase-io:8080;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_cache_bypass $http_upgrade;

        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;

        proxy_buffering off;
        proxy_request_buffering off;
        client_max_body_size 100M;
    }
}
```

**Apply Configuration:**

```bash
# Test nginx configuration
docker exec openwebui-nginx nginx -t

# Reload nginx
docker exec openwebui-nginx nginx -s reload
```

### 4. SSL Certificate Setup

**Option A: Host Certbot (Recommended)**

Continue using certbot on the host with nginx container:

```bash
# Install certbot if not already installed
sudo apt-get update
sudo apt-get install certbot

# Obtain certificate (standalone mode while nginx container handles HTTP)
sudo certbot certonly --webroot \
    -w /opt/openwebui-nginx/webroot \
    -d chat.quantabase.io

# Reload nginx after certificate issuance
docker exec openwebui-nginx nginx -s reload
```

**Renewal Setup:**

Certbot auto-renewal works automatically. Verify with:

```bash
# Test renewal
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

Add post-renewal hook to reload nginx container:

```bash
# Create renewal hook
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy/
sudo nano /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

```bash
#!/bin/bash
docker exec openwebui-nginx nginx -s reload
```

```bash
# Make executable
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

**Option B: Certbot Container**

Use a certbot container for certificate management:

```bash
# Create certificates directory
sudo mkdir -p /opt/openwebui-nginx/letsencrypt

# Obtain certificate
docker run --rm \
    -v /opt/openwebui-nginx/letsencrypt:/etc/letsencrypt \
    -v /opt/openwebui-nginx/webroot:/var/www/html \
    certbot/certbot certonly --webroot \
    -w /var/www/html \
    -d chat.quantabase.io \
    --email admin@quantabase.io \
    --agree-tos \
    --no-eff-email

# Update nginx container to mount new cert location
# (Redeploy nginx or update mounts)
```

## Migration Scenarios

### Scenario 1: Migrate Existing Host nginx Setup

**Current State:**
- nginx running on host via systemd
- Configs in `/etc/nginx/sites-available/`
- Open WebUI containers with port mappings (8081, 8082, etc.)
- SSL certificates in `/etc/letsencrypt/`

**Migration Steps:**

1. **Deploy nginx Container** (without stopping host nginx yet):
   ```bash
   sudo ./deploy-nginx-container.sh
   ```

2. **Convert Existing Configs**:
   ```bash
   sudo ./convert-nginx-configs.sh /etc/nginx/sites-available /opt/openwebui-nginx/conf.d
   ```

3. **Review Converted Configs**:
   ```bash
   # Check conversions
   ls -la /opt/openwebui-nginx/conf.d/

   # Verify proxy_pass directives changed from localhost:PORT to container:8080
   cat /opt/openwebui-nginx/conf.d/chat.quantabase.io.conf | grep proxy_pass
   ```

4. **Connect Containers to Custom Network**:
   ```bash
   sudo ./migrate-containers-to-network.sh
   # Choose Option 1 (keep port mappings for rollback safety)
   ```

5. **Test nginx Container Configuration**:
   ```bash
   docker exec openwebui-nginx nginx -t
   ```

6. **Test Connectivity**:
   ```bash
   # From nginx container to Open WebUI container
   docker exec openwebui-nginx ping -c 2 openwebui-chat-quantabase-io

   # Check if container is reachable on port 8080
   docker exec openwebui-nginx wget -O- http://openwebui-chat-quantabase-io:8080/health
   ```

7. **Switch Traffic** (only after testing):
   ```bash
   # Stop host nginx
   sudo systemctl stop nginx
   sudo systemctl disable nginx

   # Reload nginx container (it's already listening on 80/443)
   docker exec openwebui-nginx nginx -s reload
   ```

8. **Verify Production Traffic**:
   ```bash
   # Test from external client
   curl -I https://chat.quantabase.io

   # Check nginx logs
   docker logs -f openwebui-nginx
   ```

9. **Clean Up** (optional, after confirming everything works):
   ```bash
   # Recreate containers without port mappings for security
   sudo ./migrate-containers-to-network.sh
   # Choose Option 2 this time
   ```

### Scenario 2: Fresh Deployment

**Current State:**
- Clean server or no existing Open WebUI deployment
- Want containerized setup from the start

**Deployment Steps:**

1. **Deploy nginx Container**:
   ```bash
   sudo ./deploy-nginx-container.sh
   ```

2. **Deploy Open WebUI Clients** using client-manager.sh:
   ```bash
   cd /path/to/open-webui/mt
   ./client-manager.sh
   # Choose "Deploy new client"
   # Script auto-detects nginx container
   ```

   Or manually:
   ```bash
   docker run -d \
       --name openwebui-chat-quantabase-io \
       --network openwebui-network \
       -e FQDN="chat.quantabase.io" \
       -e CLIENT_NAME="chat" \
       -e GOOGLE_CLIENT_ID="your_client_id" \
       -e GOOGLE_CLIENT_SECRET="your_secret" \
       -e GOOGLE_REDIRECT_URI="https://chat.quantabase.io/oauth/google/callback" \
       -v openwebui-chat-quantabase-io-data:/app/backend/data \
       --restart unless-stopped \
       ghcr.io/imagicrafter/open-webui:main
   ```

3. **Configure nginx** (see step 3 in Quick Start)

4. **Set Up SSL** (see step 4 in Quick Start)

## Verification & Testing

### Health Checks

```bash
# Check nginx container is running
docker ps --filter "name=openwebui-nginx"

# Test nginx health endpoint
curl http://localhost/health
# Expected: "healthy"

# Check container logs
docker logs openwebui-nginx

# Verify network membership
docker network inspect openwebui-network
```

### Connectivity Tests

```bash
# Test container-to-container connectivity
docker exec openwebui-nginx ping -c 2 openwebui-chat-quantabase-io

# Test HTTP connectivity from nginx to Open WebUI
docker exec openwebui-nginx wget -O- http://openwebui-chat-quantabase-io:8080/health

# Test external HTTPS access
curl -I https://chat.quantabase.io
```

### Configuration Tests

```bash
# Validate nginx configuration
docker exec openwebui-nginx nginx -t

# Check which configs are loaded
docker exec openwebui-nginx ls -la /etc/nginx/conf.d/

# View specific config
docker exec openwebui-nginx cat /etc/nginx/conf.d/chat.quantabase.io.conf
```

## Common Operations

### Reload nginx Configuration

```bash
# After modifying configs in /opt/openwebui-nginx/conf.d/
docker exec openwebui-nginx nginx -s reload
```

### View Logs

```bash
# Follow nginx access logs
docker exec openwebui-nginx tail -f /var/log/nginx/access.log

# Follow nginx error logs
docker exec openwebui-nginx tail -f /var/log/nginx/error.log

# View Docker logs
docker logs -f openwebui-nginx

# View last 100 lines
docker logs --tail 100 openwebui-nginx
```

### Add New Client

```bash
# 1. Deploy Open WebUI container on custom network
docker run -d \
    --name openwebui-docs-example-com \
    --network openwebui-network \
    -e FQDN="docs.example.com" \
    -e CLIENT_NAME="docs" \
    -v openwebui-docs-example-com-data:/app/backend/data \
    --restart unless-stopped \
    ghcr.io/imagicrafter/open-webui:main

# 2. Create nginx config
sudo nano /opt/openwebui-nginx/conf.d/docs.example.com.conf
# (Add config using template above)

# 3. Test and reload
docker exec openwebui-nginx nginx -t
docker exec openwebui-nginx nginx -s reload

# 4. Set up SSL
sudo certbot certonly --webroot \
    -w /opt/openwebui-nginx/webroot \
    -d docs.example.com

# 5. Update nginx config with SSL paths and reload
docker exec openwebui-nginx nginx -s reload
```

### Update nginx Container

```bash
# Pull latest nginx image
docker pull nginx:alpine

# Stop and remove old container
docker stop openwebui-nginx
docker rm openwebui-nginx

# Redeploy (configs are preserved in /opt/openwebui-nginx/)
sudo ./deploy-nginx-container.sh
```

### Backup Configuration

```bash
# Backup nginx configs and SSL certs
sudo tar -czf nginx-backup-$(date +%Y%m%d).tar.gz \
    /opt/openwebui-nginx/ \
    /etc/letsencrypt/

# Restore from backup
sudo tar -xzf nginx-backup-20250117.tar.gz -C /
```

## Troubleshooting

### nginx Container Won't Start

**Check logs:**
```bash
docker logs openwebui-nginx
```

**Common issues:**
- Port 80 or 443 already in use (stop host nginx first)
- Invalid nginx.conf syntax
- Missing mounted directories

**Solutions:**
```bash
# Check ports
sudo netstat -tlnp | grep -E ':80|:443'

# Stop conflicting services
sudo systemctl stop nginx

# Validate config before starting
docker run --rm -v /opt/openwebui-nginx/nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine nginx -t
```

### Can't Reach Open WebUI Container from nginx

**Symptoms:**
- nginx returns 502 Bad Gateway
- nginx logs show "connect() failed"

**Check connectivity:**
```bash
# Verify both containers on same network
docker network inspect openwebui-network

# Test ping
docker exec openwebui-nginx ping -c 2 openwebui-chat-quantabase-io

# Check container name resolution
docker exec openwebui-nginx nslookup openwebui-chat-quantabase-io
```

**Common issues:**
- Container not connected to openwebui-network
- Wrong container name in proxy_pass directive
- Open WebUI container not running

**Solutions:**
```bash
# Connect container to network
docker network connect openwebui-network openwebui-chat-quantabase-io

# Verify container is running
docker ps --filter "name=openwebui-chat-quantabase-io"

# Check proxy_pass matches exact container name
docker exec openwebui-nginx cat /etc/nginx/conf.d/chat.quantabase.io.conf | grep proxy_pass
```

### SSL Certificate Issues

**Issue: Certificate not found**

```bash
# Check if certificates exist
docker exec openwebui-nginx ls -la /etc/letsencrypt/live/

# Verify mount
docker inspect openwebui-nginx | grep letsencrypt
```

**Solution:**
```bash
# Ensure certificates exist on host
sudo ls -la /etc/letsencrypt/live/

# Redeploy nginx with SSL mount
docker stop openwebui-nginx
docker rm openwebui-nginx
sudo ./deploy-nginx-container.sh
```

**Issue: Certificate auto-renewal not reloading nginx**

Ensure post-renewal hook is configured (see SSL Certificate Setup above).

### Configuration Not Taking Effect

**Check if file is mounted correctly:**
```bash
# View config inside container
docker exec openwebui-nginx cat /etc/nginx/conf.d/your-domain.conf

# Compare with host file
sudo cat /opt/openwebui-nginx/conf.d/your-domain.conf
```

**Solution:**
```bash
# Configs are mounted read-only, edit on host then reload
sudo nano /opt/openwebui-nginx/conf.d/your-domain.conf
docker exec openwebui-nginx nginx -t
docker exec openwebui-nginx nginx -s reload
```

### High Memory or CPU Usage

**Check nginx stats:**
```bash
docker stats openwebui-nginx
```

**Common causes:**
- Too many worker processes
- Connection leaks
- Slow backend (Open WebUI container issues)

**Solutions:**
```bash
# Check nginx worker configuration
docker exec openwebui-nginx cat /etc/nginx/nginx.conf | grep worker_processes

# Check Open WebUI container health
docker ps --filter "name=openwebui-"
docker stats $(docker ps --filter "name=openwebui-" --format "{{.Names}}")

# Check nginx connections
docker exec openwebui-nginx cat /var/log/nginx/access.log | tail -100
```

## Rollback Procedures

### Rollback to Host nginx

If you need to revert to host nginx:

```bash
# 1. Stop nginx container
docker stop openwebui-nginx

# 2. Start host nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# 3. Verify host nginx is working
sudo systemctl status nginx
curl -I http://localhost

# 4. Optional: Remove nginx container (keeps configs)
docker rm openwebui-nginx

# 5. Optional: Restore original port mappings to Open WebUI containers
# (Use migrate-containers-to-network.sh Option 2 in reverse, or manually recreate)
```

**Note:** If you used Migration Option 1 (kept port mappings), rollback is instant - just stop nginx container and start host nginx. If you used Option 2 (removed port mappings), you'll need to recreate Open WebUI containers with `-p` flags.

### Emergency Fallback

If everything breaks:

```bash
# 1. Stop all containers
docker stop openwebui-nginx $(docker ps --filter "name=openwebui-" --format "{{.Names}}")

# 2. Start host nginx
sudo systemctl start nginx

# 3. Recreate Open WebUI containers with port mappings
# (Use client-manager.sh or manually with -p flags)

# 4. Restore host nginx configs
sudo cp /etc/nginx/sites-available/*.conf.backup /etc/nginx/sites-available/
sudo nginx -t
sudo systemctl reload nginx
```

## Best Practices

### Security

- **Remove Unnecessary Port Mappings**: After migration, use Option 2 to recreate containers without `-p` flags for better isolation
- **Read-Only Mounts**: nginx.conf and configs are mounted read-only (`:ro` flag)
- **SSL/TLS**: Always use HTTPS in production with valid certificates
- **Network Isolation**: Use custom network instead of default bridge
- **Regular Updates**: Keep nginx container image updated

### Performance

- **Worker Processes**: Set to `auto` to match CPU cores (default in config)
- **Gzip Compression**: Enabled by default for static assets
- **Connection Pooling**: Increase `worker_connections` if needed for high traffic
- **Buffer Sizes**: Adjust `client_max_body_size` based on upload requirements

### Maintenance

- **Backup Regularly**: Use backup command above before making changes
- **Test Before Reload**: Always run `nginx -t` before `nginx -s reload`
- **Monitor Logs**: Set up log rotation and monitoring
- **Document Changes**: Keep notes on custom configurations
- **Version Control**: Consider storing `/opt/openwebui-nginx/conf.d/` in git

### Monitoring

```bash
# Create simple monitoring script
cat > /opt/openwebui-nginx/check-health.sh << 'EOF'
#!/bin/bash
if ! docker ps | grep -q openwebui-nginx; then
    echo "ERROR: nginx container not running"
    exit 1
fi

if ! curl -sf http://localhost/health > /dev/null; then
    echo "ERROR: nginx health check failed"
    exit 1
fi

echo "OK: nginx healthy"
EOF

chmod +x /opt/openwebui-nginx/check-health.sh

# Add to crontab for monitoring
# */5 * * * * /opt/openwebui-nginx/check-health.sh
```

## Advanced Configuration

### Custom nginx.conf Settings

Edit the main configuration:

```bash
sudo nano /opt/openwebui-nginx/nginx.conf

# Test changes
docker exec openwebui-nginx nginx -t

# Reload
docker exec openwebui-nginx nginx -s reload
```

### Rate Limiting

Add to `/opt/openwebui-nginx/nginx.conf` in `http` block:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=one:10m rate=10r/s;
limit_req_status 429;
```

Then in server block:

```nginx
location / {
    limit_req zone=one burst=20 nodelay;
    proxy_pass http://openwebui-chat-quantabase-io:8080;
    # ... other settings
}
```

### Custom Error Pages

```bash
# Create error pages directory
sudo mkdir -p /opt/openwebui-nginx/error-pages

# Create custom 502 page
sudo nano /opt/openwebui-nginx/error-pages/502.html

# Update server block
sudo nano /opt/openwebui-nginx/conf.d/your-domain.conf
```

Add to server block:

```nginx
error_page 502 /502.html;
location = /502.html {
    root /usr/share/nginx/html;
    internal;
}
```

### IP Whitelisting

Add to specific location or server block:

```nginx
location /admin {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://openwebui-chat-quantabase-io:8080;
}
```

## Integration with client-manager.sh

The `client-manager.sh` script automatically detects containerized nginx:

```bash
# Auto-detection logic
if docker ps --filter "name=openwebui-nginx" | grep -q openwebui-nginx; then
    # Use containerized template
    template="/path/to/nginx-template-containerized.conf"
else
    # Use host nginx template
    template="/path/to/nginx-template.conf"
fi
```

**Features:**
- Generates configs using container names instead of localhost:PORT
- Provides containerized-specific setup instructions
- Creates configs in appropriate directory for each setup type

## References

- [nginx Docker Official Image](https://hub.docker.com/_/nginx)
- [Docker Networks](https://docs.docker.com/network/)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)
- [nginx Configuration Guide](https://nginx.org/en/docs/)

## Support

For issues with these scripts:
1. Check troubleshooting section above
2. Review nginx container logs: `docker logs openwebui-nginx`
3. Verify network configuration: `docker network inspect openwebui-network`
4. Test individual components (nginx config, container connectivity, SSL certs)

## License

These scripts are part of the Open WebUI project and follow the same license terms.
