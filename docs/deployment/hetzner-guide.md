# mAI Hetzner Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying mAI on Hetzner Cloud, suitable for beginners.

## Prerequisites
- Hetzner Cloud account
- Domain name (for SSL)
- GitHub account (for container registry)
- Basic command line knowledge

## Table of Contents
1. [Server Setup](#1-server-setup)
2. [Initial Configuration](#2-initial-configuration)
3. [Docker Installation](#3-docker-installation)
4. [Deploy mAI](#4-deploy-mai)
5. [SSL Setup](#5-ssl-setup)
6. [Monitoring](#6-monitoring)
7. [Backup Strategy](#7-backup-strategy)
8. [Maintenance](#8-maintenance)

## 1. Server Setup

### 1.1 Create Hetzner Server
1. Log into [Hetzner Cloud Console](https://console.hetzner.cloud)
2. Click "New Server"
3. Choose configuration:
   - **Location**: Falkenstein (fsn1) or Nuremberg (nbg1)
   - **Image**: Ubuntu 24.04
   - **Type**: CPX31 (4 vCPU, 8GB RAM) minimum
   - **Storage**: 80GB NVMe SSD
   - **Network**: IPv4 + IPv6

4. Add SSH key (recommended) or use password
5. Set hostname: `mai-prod-01`
6. Click "Create & Buy now"

### 1.2 Connect to Server
```bash
# Using SSH key
ssh root@YOUR_SERVER_IP

# Or with password
ssh root@YOUR_SERVER_IP
# Enter password when prompted
```

## 2. Initial Configuration

### 2.1 Update System
```bash
# Update package list and upgrade
apt update && apt upgrade -y

# Install essential packages
apt install -y \
    curl \
    wget \
    git \
    htop \
    ufw \
    fail2ban \
    unattended-upgrades
```

### 2.2 Create Non-Root User
```bash
# Create user
adduser mai-admin

# Add to sudo group
usermod -aG sudo mai-admin

# Copy SSH keys (if using)
rsync --archive --chown=mai-admin:mai-admin ~/.ssh /home/mai-admin

# Switch to new user
su - mai-admin
```

### 2.3 Configure Firewall
```bash
# Allow SSH
sudo ufw allow OpenSSH

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

### 2.4 Configure Fail2ban
```bash
# Create local config
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit config
sudo nano /etc/fail2ban/jail.local

# Find [sshd] section and ensure:
# enabled = true
# maxretry = 3
# bantime = 3600

# Restart fail2ban
sudo systemctl restart fail2ban
```

## 3. Docker Installation

### 3.1 Install Docker
```bash
# Install prerequisites
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes
exit
ssh mai-admin@YOUR_SERVER_IP
```

### 3.2 Verify Docker Installation
```bash
# Check Docker version
docker --version

# Run test container
docker run hello-world
```

## 4. Deploy mAI

### 4.1 Create Directory Structure
```bash
# Create deployment directory
mkdir -p ~/mai-deployment/{data,config,backups}
cd ~/mai-deployment

# Create environment file
nano .env
```

### 4.2 Configure Environment
Add to `.env`:
```bash
# Basic Configuration
WEBUI_NAME=mAI
WEBUI_URL=https://ai.yourdomain.com
WEBUI_SECRET_KEY=$(openssl rand -hex 32)

# Database
DATABASE_URL=sqlite:////app/backend/data/webui.db

# Ollama Connection
OLLAMA_BASE_URL=http://ollama:11434

# Authentication
WEBUI_AUTH=True
JWT_EXPIRES_IN=3600

# SSL (managed by proxy)
WEBUI_SSL=False

# Performance
WORKERS=4
```

### 4.3 Create Docker Compose File
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  mai:
    image: ghcr.io/pilpat/mai:v0.0.0
    container_name: mai-app
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./data:/app/backend/data
      - ./config:/app/backend/config
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    container_name: mai-ollama
    restart: unless-stopped
    volumes:
      - ollama-data:/root/.ollama
    ports:
      - "127.0.0.1:11434:11434"

  nginx:
    image: nginx:alpine
    container_name: mai-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - mai

volumes:
  ollama-data:
```

### 4.4 Create Nginx Configuration
Create `nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream mai_backend {
        server mai:8080;
    }

    server {
        listen 80;
        server_name ai.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name ai.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        client_max_body_size 100M;

        location / {
            proxy_pass http://mai_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

### 4.5 Deploy Application
```bash
# Pull images
docker compose pull

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f mai
```

## 5. SSL Setup

### 5.1 Install Certbot
```bash
# Install snapd
sudo apt install snapd

# Install certbot
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### 5.2 Obtain SSL Certificate
```bash
# Stop nginx temporarily
docker compose stop nginx

# Get certificate
sudo certbot certonly --standalone -d ai.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/ai.yourdomain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/ai.yourdomain.com/privkey.pem ./ssl/
sudo chown mai-admin:mai-admin ./ssl/*

# Start nginx
docker compose start nginx
```

### 5.3 Auto-Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab
crontab -e

# Add line:
0 2 * * * /usr/bin/certbot renew --quiet && docker compose restart nginx
```

## 6. Monitoring

### 6.1 Basic Monitoring
```bash
# Create monitoring script
nano ~/mai-deployment/monitor.sh
```

Add content:
```bash
#!/bin/bash
# mAI Health Check

echo "=== mAI System Status ==="
echo "Date: $(date)"
echo

echo "=== Docker Services ==="
docker compose ps

echo -e "\n=== Resource Usage ==="
docker stats --no-stream

echo -e "\n=== Disk Usage ==="
df -h | grep -E "^/dev/"

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Recent Logs ==="
docker compose logs --tail=20 mai
```

Make executable:
```bash
chmod +x ~/mai-deployment/monitor.sh
```

### 6.2 Setup Alerts
Create `~/mai-deployment/health-check.sh`:
```bash
#!/bin/bash
# Health check with email alerts

HEALTH_URL="https://ai.yourdomain.com/health"
EMAIL="admin@yourdomain.com"

if ! curl -sf $HEALTH_URL > /dev/null; then
    echo "mAI is DOWN at $(date)" | mail -s "ALERT: mAI Health Check Failed" $EMAIL
    docker compose restart mai
fi
```

Add to crontab:
```bash
*/5 * * * * /home/mai-admin/mai-deployment/health-check.sh
```

## 7. Backup Strategy

### 7.1 Automated Backups
Create `~/mai-deployment/backup.sh`:
```bash
#!/bin/bash
# mAI Backup Script

BACKUP_DIR="/home/mai-admin/mai-deployment/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup
echo "Starting backup at $(date)"

# Stop services for consistency
docker compose stop mai

# Backup data
tar -czf "$BACKUP_DIR/mai-backup-$DATE.tar.gz" \
    -C /home/mai-admin/mai-deployment \
    data config .env

# Start services
docker compose start mai

# Upload to Hetzner Storage Box (optional)
# rsync -avz "$BACKUP_DIR/mai-backup-$DATE.tar.gz" u12345@u12345.your-storagebox.de:/backups/

# Clean old backups
find "$BACKUP_DIR" -name "mai-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed at $(date)"
```

Schedule daily backups:
```bash
chmod +x ~/mai-deployment/backup.sh
crontab -e
# Add: 0 3 * * * /home/mai-admin/mai-deployment/backup.sh
```

## 8. Maintenance

### 8.1 Regular Updates
```bash
# Update mAI
cd ~/mai-deployment
docker compose pull
docker compose up -d

# Update system
sudo apt update && sudo apt upgrade -y

# Clean Docker
docker system prune -af --volumes
```

### 8.2 Troubleshooting Commands
```bash
# View logs
docker compose logs -f mai

# Restart service
docker compose restart mai

# Check disk space
df -h

# Check memory
free -h

# Database backup
docker compose exec mai sqlite3 /app/backend/data/webui.db ".backup /app/backend/data/backup.db"

# Access container shell
docker compose exec mai bash
```

### 8.3 Performance Tuning
Edit `/etc/sysctl.conf`:
```bash
# Network optimizations
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Apply changes
sudo sysctl -p
```

## Quick Reference

### Essential Commands
```bash
# Start mAI
cd ~/mai-deployment && docker compose up -d

# Stop mAI
cd ~/mai-deployment && docker compose down

# View logs
cd ~/mai-deployment && docker compose logs -f

# Backup
~/mai-deployment/backup.sh

# Monitor
~/mai-deployment/monitor.sh
```

### Important Paths
- Application: `/home/mai-admin/mai-deployment/`
- Data: `/home/mai-admin/mai-deployment/data/`
- Backups: `/home/mai-admin/mai-deployment/backups/`
- Logs: `docker compose logs`

### Support Contacts
- Hetzner Support: https://console.hetzner.cloud/support
- mAI Documentation: Your GitHub repository
- Emergency: Create backup, then rollback to v0-stable tag

## Security Checklist
- [ ] Firewall configured and enabled
- [ ] Fail2ban active
- [ ] SSL certificates installed
- [ ] Regular updates scheduled
- [ ] Backups automated
- [ ] Monitoring active
- [ ] Strong passwords set
- [ ] SSH key authentication only

This completes your production deployment on Hetzner!