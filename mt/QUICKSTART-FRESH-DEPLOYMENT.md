# Quick Start: Fresh Digital Ocean Deployment

This guide walks you through deploying Open WebUI multi-tenant setup on a fresh Digital Ocean droplet using the Docker one-click image.

## Prerequisites

- Digital Ocean account
- Domain name(s) configured with DNS pointing to your server
- Google OAuth credentials (optional, for authentication)
- SSH key pair for secure authentication

## Security Note: Use a Dedicated Deployment User ⭐ Recommended

**For production deployments, avoid using root**. Instead, create a dedicated deployment user with appropriate permissions.

**Why?**
- ✅ Better security (limited privileges)
- ✅ Clear audit trail
- ✅ Easier to manage and revoke access
- ✅ Industry best practice

**Two Options:**

### Option A: Automated Setup (Cloud-Init) - Recommended for New Droplets

Use cloud-init to automatically create the deployment user during droplet creation. See **[mt/setup/README.md](setup/README.md)** for detailed instructions.

**Quick version:**
1. Edit `mt/setup/cloud-init-user-data.yaml` with your SSH public key
2. Paste the entire file as "User Data" when creating your droplet
3. SSH as `deployer` user (root is automatically disabled)

### Option B: Manual Setup - For Existing Droplets

If you already created a droplet or prefer manual setup:

```bash
ssh root@YOUR_DROPLET_IP
git clone https://github.com/imagicrafter/open-webui.git
cd open-webui/mt/setup
chmod +x create-deployment-user.sh
sudo ./create-deployment-user.sh
# Follow interactive prompts
# Test SSH as deployer before disabling root
```

**See [mt/setup/README.md](setup/README.md) for complete documentation.**

---

**The rest of this guide uses `/root/` paths for simplicity. If using the deployer user (recommended), replace:**
- `/root/` → `/home/deployer/` or `~/`
- `ssh root@IP` → `ssh deployer@IP`

---

## Step 1: Create Digital Ocean Droplet

1. **Create new droplet** using Docker one-click image:
   - **Image**: [Docker 20.04](https://github.com/digitalocean/droplet-1-clicks/tree/master/docker-20-04)
   - **Size**: Minimum 2GB RAM (4GB recommended for production)
   - **Region**: Choose closest to your users
   - **SSH**: Add your SSH key

2. **Note your droplet's IP address** from the Digital Ocean dashboard

## Step 2: Connect and Setup Repository

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Clone the Open WebUI repository
cd /root
git clone https://github.com/imagicrafter/open-webui.git
cd open-webui

# Optional: Check out specific branch if needed
# git checkout main
```

## Step 3: Deploy nginx Container (One-Time Setup)

```bash
cd /root/open-webui/mt/nginx-container

# Deploy nginx container
sudo ./deploy-nginx-container.sh
```

**What This Does:**
- Creates `openwebui-network` Docker bridge network
- Deploys `openwebui-nginx` container
- Sets up config directory at `/opt/openwebui-nginx/`
- Mounts SSL certificates from `/etc/letsencrypt/` (if available)

**Expected Output:**
```
╔════════════════════════════════════════╗
║   Deploy Containerized nginx           ║
╚════════════════════════════════════════╝

✅ Created network 'openwebui-network'
✅ Created directories
✅ Created main nginx.conf
✅ nginx container deployed
✅ nginx container is running
✅ Health check passed
```

## Step 4: Deploy Your First Open WebUI Client

```bash
cd /root/open-webui/mt

# Run the client manager
./client-manager.sh
```

**Interactive Menu:**
1. Choose option **2) Create New Deployment**
2. Enter client name (e.g., `chat`, `docs`, `support`)
3. Enter domain (e.g., `chat.yourdomain.com`)
4. Script will auto-detect nginx container and deploy on custom network
5. Confirm deployment

**Example Output:**
```
✓ Detected containerized nginx - deploying on openwebui-network
  (No port mapping needed - container-to-container communication)

✅ chat Open WebUI started successfully!
🌐 Access: https://chat.yourdomain.com
   (Container accessible only via nginx - no direct port access)
📦 Volume: openwebui-chat-yourdomain-com-data
🐳 Container: openwebui-chat-yourdomain-com

Next steps:
1. Configure nginx for chat.yourdomain.com using client-manager.sh option 5
2. Set up SSL certificate for chat.yourdomain.com
```

## Step 5: Configure nginx for the Domain

**Option A: Using client-manager.sh (Recommended)**

```bash
# Still in /root/open-webui/mt
./client-manager.sh

# Choose option 5: Generate nginx Configuration
# Select the client you just created
# Script will generate config in /tmp/ with instructions
```

Follow the displayed instructions to copy and activate the config.

**Option B: Manual Configuration**

The client-manager generates the config file automatically. Just copy it:

```bash
# Copy the generated config (replace DOMAIN with your actual domain)
sudo cp /tmp/DOMAIN-nginx.conf /opt/openwebui-nginx/conf.d/DOMAIN.conf

# Test nginx configuration
docker exec openwebui-nginx nginx -t

# Reload nginx
docker exec openwebui-nginx nginx -s reload
```

## Step 6: Set Up SSL Certificate

```bash
# Install certbot on the host
sudo apt-get update
sudo apt-get install -y certbot

# Obtain SSL certificate
sudo certbot certonly --webroot \
    -w /opt/openwebui-nginx/webroot \
    -d chat.yourdomain.com \
    --email your-email@example.com \
    --agree-tos \
    --no-eff-email

# Reload nginx to activate SSL
docker exec openwebui-nginx nginx -s reload
```

**Auto-Renewal Setup:**

Create a renewal hook to reload nginx container after renewal:

```bash
# Create renewal hook
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy/
sudo nano /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

Add this content:

```bash
#!/bin/bash
docker exec openwebui-nginx nginx -s reload
```

Make it executable:

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

# Test renewal
sudo certbot renew --dry-run
```

## Step 7: Verify Deployment

```bash
# Check nginx container is running
docker ps --filter "name=openwebui-nginx"

# Check your Open WebUI container is running
docker ps --filter "name=openwebui-chat"

# Test connectivity from nginx to Open WebUI
docker exec openwebui-nginx ping -c 2 openwebui-chat-yourdomain-com

# Check nginx access logs
docker logs openwebui-nginx --tail 20

# Access your site
curl -I https://chat.yourdomain.com
```

## Step 8: Deploy Additional Clients (Optional)

Repeat Steps 4-6 for each additional client/domain:

```bash
cd /root/open-webui/mt
./client-manager.sh
# Choose option 2 again
```

Each client will:
- Automatically deploy on `openwebui-network`
- Use FQDN-based container naming
- Be isolated with its own data volume

## Architecture Overview

After deployment, you'll have:

```
┌─────────────────────────────────────────┐
│          openwebui-network               │
│                                          │
│  ┌──────────────┐   ┌─────────────────┐ │
│  │ openwebui-   │   │ openwebui-chat- │ │
│  │ nginx        │──▶│ yourdomain-com  │ │
│  │              │   │                 │ │
│  │ :80, :443    │   │ :8080           │ │
│  └──────────────┘   └─────────────────┘ │
│                                          │
│                     ┌─────────────────┐ │
│                     │ openwebui-docs- │ │
│                     │ yourdomain-com  │ │
│                     │ :8080           │ │
│                     └─────────────────┘ │
└─────────────────────────────────────────┘
```

## Common Post-Deployment Tasks

### View All Deployments

```bash
cd /root/open-webui/mt
./client-manager.sh
# Choose option 1: View Deployment Status
```

### View Container Logs

```bash
# Real-time logs
docker logs -f openwebui-chat-yourdomain-com

# Last 100 lines
docker logs --tail 100 openwebui-chat-yourdomain-com
```

### Restart a Client

```bash
cd /root/open-webui/mt
./client-manager.sh
# Choose option 3: Manage Client Deployment
# Select the client
# Choose restart option
```

### Update nginx Configuration

```bash
# Edit config
sudo nano /opt/openwebui-nginx/conf.d/chat.yourdomain.com.conf

# Test changes
docker exec openwebui-nginx nginx -t

# Apply changes
docker exec openwebui-nginx nginx -s reload
```

### Backup Client Data

```bash
# List all volumes
docker volume ls | grep openwebui

# Backup a specific client's volume
docker run --rm \
    -v openwebui-chat-yourdomain-com-data:/data \
    -v /root/backups:/backup \
    alpine tar czf /backup/chat-backup-$(date +%Y%m%d).tar.gz /data
```

## Troubleshooting

### Can't Access Site (502 Bad Gateway)

```bash
# Check containers are running
docker ps --filter "name=openwebui-"

# Verify network connectivity
docker exec openwebui-nginx ping -c 2 openwebui-chat-yourdomain-com

# Check Open WebUI logs
docker logs openwebui-chat-yourdomain-com --tail 50

# Check nginx logs
docker logs openwebui-nginx --tail 50
```

### SSL Certificate Issues

```bash
# Check certificates exist
sudo ls -la /etc/letsencrypt/live/

# Verify nginx has access
docker exec openwebui-nginx ls -la /etc/letsencrypt/live/

# Test certificate
curl -vI https://chat.yourdomain.com 2>&1 | grep -i certificate
```

### Container Won't Start

```bash
# View container logs
docker logs openwebui-chat-yourdomain-com

# Check for port conflicts (if using host nginx mode)
sudo netstat -tlnp | grep 8081

# Inspect container
docker inspect openwebui-chat-yourdomain-com
```

## Next Steps

- **Configure OAuth**: Update Google OAuth credentials for production
- **Set Up Monitoring**: Configure health checks and alerts
- **Backup Strategy**: Implement automated volume backups
- **Scaling**: Deploy additional clients for different teams/projects
- **Custom Branding**: Upload custom logos and branding assets

## Documentation References

- **Detailed nginx Setup**: `mt/nginx-container/README.md`
- **Client Manager Guide**: `mt/README.md`
- **OAuth Configuration**: `.claude/CLAUDE.md` (Project Status section)

## Support

For issues:
1. Check logs: `docker logs CONTAINER_NAME`
2. Review nginx config: `docker exec openwebui-nginx nginx -t`
3. Verify network: `docker network inspect openwebui-network`
4. Consult troubleshooting guides in `mt/nginx-container/README.md`

---

**Summary: One-Command Setup**

```bash
# 1. Deploy nginx (one-time)
cd /root/open-webui/mt/nginx-container && sudo ./deploy-nginx-container.sh

# 2. Deploy client (repeat for each domain)
cd /root/open-webui/mt && ./client-manager.sh
# Choose option 2, enter name and domain

# 3. Configure nginx (auto-generated)
./client-manager.sh
# Choose option 5, follow instructions

# 4. Set up SSL
sudo certbot certonly --webroot -w /opt/openwebui-nginx/webroot -d YOUR_DOMAIN
docker exec openwebui-nginx nginx -s reload
```

That's it! Your multi-tenant Open WebUI is ready. 🚀
