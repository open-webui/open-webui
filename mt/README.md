# Multi-Tenant Open WebUI

This directory contains scripts for running multiple isolated Open WebUI instances for different clients.

## Overview

Each client gets their own:
- 🔒 **Isolated container** with unique name
- 💾 **Dedicated data volume** (separate chat history, settings, etc.)
- 🌐 **Custom domain** and port
- 🏷️ **Branded interface** with client name
- 🔐 **Same OAuth configuration** (martins.net domain restriction)

## Quick Start

### Start Pre-configured Clients
```bash
# Start ACME Corp instance (port 8081)
./start-acme-corp.sh

# Start Beta Client instance (port 8082)
./start-beta-client.sh
```

### Start Custom Client
```bash
# Usage: ./start-template.sh CLIENT_NAME PORT DOMAIN
./start-template.sh xyz-corp 8083 xyz.yourdomain.com
```

### Manage All Clients
```bash
# Show help and available commands
./manage-clients.sh

# List all client containers
./manage-clients.sh list

# Stop all client containers
./manage-clients.sh stop

# Start all stopped client containers
./manage-clients.sh start

# View logs for specific client
./manage-clients.sh logs acme-corp
```

## File Structure

```
mt/
├── README.md                 # This file
├── start-template.sh         # Template for creating client instances
├── start-acme-corp.sh        # Pre-configured ACME Corp launcher
├── start-beta-client.sh      # Pre-configured Beta Client launcher
└── manage-clients.sh         # Multi-client management tool
```

## Container Naming Convention

| Client | Container Name | Port | Domain |
|--------|---------------|------|---------|
| ACME Corp | `openwebui-acme-corp` | 8081 | acme.yourdomain.com |
| Beta Client | `openwebui-beta-client` | 8082 | beta.yourdomain.com |
| Custom | `openwebui-CLIENT_NAME` | Custom | Custom |

## Volume Naming Convention

Each client gets an isolated Docker volume:
- `openwebui-acme-corp-data`
- `openwebui-beta-client-data`
- `openwebui-CLIENT_NAME-data`

## Adding New Clients

### Method 1: Use Template Script
```bash
./start-template.sh new-client 8084 newclient.yourdomain.com
```

### Method 2: Create Dedicated Script
1. Copy an existing client script:
   ```bash
   cp start-acme-corp.sh start-new-client.sh
   ```

2. Edit the new script to change the client name, port, and domain:
   ```bash
   ${SCRIPT_DIR}/start-template.sh new-client 8084 newclient.yourdomain.com
   ```

3. Make it executable:
   ```bash
   chmod +x start-new-client.sh
   ```

## Individual Container Management

```bash
# Stop specific client
docker stop openwebui-CLIENT_NAME

# Start specific client
docker start openwebui-CLIENT_NAME

# Restart specific client
docker restart openwebui-CLIENT_NAME

# View logs for specific client
docker logs -f openwebui-CLIENT_NAME

# Remove client (CAUTION: This deletes the container but preserves data volume)
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME
```

## Port Management

**Used Ports:**
- 8081: ACME Corp
- 8082: Beta Client

**Available Ports:**
- 8083-8099: Available for new clients

**Port Conflict Check:**
```bash
# Check what ports are in use
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Check specific port
sudo lsof -i :8083
```

## nginx Configuration

For each client, add an nginx server block:

```nginx
server {
    listen 443 ssl http2;
    server_name acme.yourdomain.com;

    # SSL configuration here...

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## OAuth Configuration

All clients share the same Google OAuth configuration:
- **Domain Restriction:** `martins.net`
- **Redirect URI Pattern:** `https://CLIENT_DOMAIN/oauth/google/callback`

Update Google Cloud Console with each new client domain.

## Source Code Update Process

This system uses a custom fork of Open WebUI with QuantaBase branding. Follow this process to update to the latest Open WebUI version while preserving custom modifications.

### Repository Setup

**Custom Fork:** `https://github.com/imagicrafter/open-webui`
**Container Image:** `ghcr.io/imagicrafter/open-webui:main`
**Upstream:** `https://github.com/open-webui/open-webui`

### Your Customizations (What to Preserve)

The following files/directories contain your QuantaBase customizations:

**✅ Committed Custom Files:**
- `assets/logos/` - Custom QuantaBase branding assets
- `backend/open_webui/static/favicon.png` - Replaced favicon
- `backend/open_webui/static/logo.png` - Replaced logo
- `backend/open_webui/static/swagger-ui/favicon.png` - API docs favicon
- `static/favicon.png` and `static/static/` - Additional static file replacements
- `favicon_backup/` - Backup of original files
- `.claude/` - Claude Code session files
- `docker-start.md` - Custom documentation

**⚠️ Local-Only Files (Need to commit):**
- `mt/` - Multi-tenant client management system
- `start.sh` - Enhanced QuantaBase startup script

### Update Workflow (Branching Strategy)

This strategy ensures your customizations are never lost during updates:

#### 1. Prepare for Update

```bash
# Navigate to your local fork
cd /path/to/your/open-webui

# Ensure upstream remote exists
git remote add upstream https://github.com/open-webui/open-webui.git || true

# Commit any local changes first
git add mt/ start.sh
git commit -m "Add multi-tenant system and enhanced start script"
git push origin main
```

#### 2. Create Branching Structure

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create quantabase-branded branch (preserves all your customizations)
git checkout -b quantabase-branded
git push origin quantabase-branded

# Create update branch from quantabase-branded
git checkout -b quantabase-update
```

#### 3. Pull Upstream Changes

```bash
# Fetch latest from upstream
git fetch upstream

# Merge upstream changes into update branch
git merge upstream/main

# Handle merge conflicts:
# - Choose YOUR version for all files in "Your Customizations" list above
# - Accept UPSTREAM version for core Open WebUI functionality
# - Manually merge any files that need both changes
```

#### 4. Preserve Your Customizations

If conflicts occur with your custom files, resolve them like this:

```bash
# For custom branding files, keep your version:
git checkout --ours assets/logos/
git checkout --ours backend/open_webui/static/favicon.png
git checkout --ours backend/open_webui/static/logo.png
# ... repeat for all custom files

# For core functionality, accept upstream:
git checkout --theirs src/lib/components/
git checkout --theirs backend/open_webui/routers/
# ... etc for core files

# Commit the resolution
git add .
git commit -m "Merge upstream $(date +%Y-%m-%d) - preserved QuantaBase customizations"
```

#### 5. Merge Back to Branded Branch

```bash
# Merge update branch into quantabase-branded
git checkout quantabase-branded
git merge quantabase-update

# Push updated branded branch
git push origin quantabase-branded
```

#### 6. Build and Test Locally

```bash
# Still on quantabase-update branch
# Build your updated image locally
docker build -t ghcr.io/imagicrafter/open-webui:test .

# Test with a temporary container
docker run -d --name test-openwebui -p 8090:8080 \
  -e GOOGLE_CLIENT_ID=your_client_id \
  -e GOOGLE_CLIENT_SECRET=your_secret \
  -e GOOGLE_REDIRECT_URI=http://127.0.0.1:8090/oauth/google/callback \
  -e ENABLE_OAUTH_SIGNUP=true \
  -e OAUTH_ALLOWED_DOMAINS=martins.net \
  -e WEBUI_NAME="QuantaBase Test" \
  ghcr.io/imagicrafter/open-webui:test

# Test checklist:
# ✅ OAuth login works
# ✅ QuantaBase branding appears correctly
# ✅ Core Open WebUI features function
# ✅ Multi-tenant scripts work (if testing locally)

# Clean up test container
docker stop test-openwebui && docker rm test-openwebui
```

#### 7. Merge to Main Branch

```bash
# If tests pass, merge quantabase-update into main
git checkout main
git merge quantabase-update
git push origin main

# Tag the release
git tag -a v$(date +%Y.%m.%d) -m "Update to latest Open WebUI $(date +%Y-%m-%d)"
git push origin --tags

# Clean up update branch
git branch -d quantabase-update
git push origin --delete quantabase-update
```

#### 8. Deploy to Production

```bash
# SSH to production server
ssh user@your-production-server

# Navigate to deployment directory
cd /path/to/open-webui

# Pull from main branch
git pull origin main
```

#### 9. Build Production Image

```bash
# Build production image from updated code
docker build -t ghcr.io/imagicrafter/open-webui:main .

# Or pull from GitHub Container Registry if auto-build is set up
# docker pull ghcr.io/imagicrafter/open-webui:main
```

#### 10. Restart Client Containers

```bash
# Update all client deployments with new image
./mt/manage-clients.sh stop
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm
./mt/manage-clients.sh start

# Verify all clients are running with updated image
./mt/manage-clients.sh list
docker images ghcr.io/imagicrafter/open-webui
```

#### 4. GitHub Actions (Automatic Image Build)

Your GitHub repository should have Actions configured to automatically build and push to GitHub Container Registry when you push to main. If not set up, the workflow file should be:

```yaml
# .github/workflows/docker.yml
name: Build and Push Docker Image
on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Log in to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ghcr.io/imagicrafter/open-webui:main
```

#### 5. Update Production Deployments

```bash
# SSH to production server
ssh user@your-production-server

# Navigate to deployment directory
cd /path/to/open-webui

# Pull latest code (optional - for reference)
git pull origin main

# Pull updated image
docker pull ghcr.io/imagicrafter/open-webui:main

# Update all client deployments
./mt/manage-clients.sh stop
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm
./mt/manage-clients.sh start

# Verify all clients are running
./mt/manage-clients.sh list
```

### Rollback Process

If an update causes issues:

```bash
# Check recent image tags
docker images ghcr.io/imagicrafter/open-webui

# Use a previous tag
docker tag ghcr.io/imagicrafter/open-webui:v2024.01.15 ghcr.io/imagicrafter/open-webui:main

# Restart clients with previous version
./mt/manage-clients.sh stop
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm
./mt/manage-clients.sh start
```

### Custom Branding Checklist

When updating, ensure these custom elements are preserved:

- [ ] QuantaBase logos in `assets/logos/`
- [ ] Custom favicon files
- [ ] Environment variable configurations
- [ ] OAuth settings and domain restrictions
- [ ] Any custom styling or themes

## Updates and Maintenance

### Image Updates (New Open WebUI Version)

To update a client to the latest Open WebUI version while preserving all data:

```bash
# Stop and remove container (keeps volume and data)
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME

# Pull latest image
docker pull ghcr.io/imagicrafter/open-webui:main

# Recreate with new image (data automatically preserved)
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

**Example - Update imagicrafter client:**
```bash
docker stop openwebui-imagicrafter && docker rm openwebui-imagicrafter
docker pull ghcr.io/imagicrafter/open-webui:main
./start-template.sh imagicrafter 8081
```

### Configuration Updates

To update environment variables or settings:

```bash
# Stop and remove container
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME

# Recreate with new configuration (data preserved)
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

### Fresh Start (Delete All Data)

⚠️ **WARNING: This permanently deletes all client data**

```bash
# Stop and remove container AND volume
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME
docker volume rm openwebui-CLIENT_NAME-data

# Recreate from scratch
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

### Bulk Updates

Update all clients to latest image:

```bash
# Stop all clients
./manage-clients.sh stop

# Pull latest image
docker pull ghcr.io/imagicrafter/open-webui:main

# Remove all containers (keeps volumes)
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm

# Restart all clients (they'll use the new image)
./manage-clients.sh start
```

### Volume Management

```bash
# List all client volumes
docker volume ls | grep openwebui

# Check volume disk usage
docker system df -v | grep openwebui

# Remove unused volumes (DANGER - only if you're sure)
docker volume prune
```

## Data Backup

Each client's data is stored in a named Docker volume:

```bash
# List all client volumes
docker volume ls | grep openwebui

# Backup client data
docker run --rm -v openwebui-CLIENT_NAME-data:/data -v $(pwd):/backup alpine tar czf /backup/CLIENT_NAME-backup.tar.gz -C /data .

# Restore client data
docker run --rm -v openwebui-CLIENT_NAME-data:/data -v $(pwd):/backup alpine tar xzf /backup/CLIENT_NAME-backup.tar.gz -C /data

# Backup all client data
for volume in $(docker volume ls --filter name=openwebui- --format "{{.Name}}"); do
  client=$(echo $volume | sed 's/openwebui-//' | sed 's/-data//')
  docker run --rm -v $volume:/data -v $(pwd):/backup alpine tar czf /backup/${client}-backup-$(date +%Y%m%d).tar.gz -C /data .
done
```

## Troubleshooting

### Container Won't Start
```bash
# Check if container name already exists
docker ps -a | grep openwebui-CLIENT_NAME

# Check port conflicts
sudo lsof -i :PORT_NUMBER

# Check logs
docker logs openwebui-CLIENT_NAME
```

### Permission Issues
```bash
# Ensure scripts are executable
chmod +x *.sh
```

### OAuth Issues
1. Verify redirect URI in Google Cloud Console
2. Check domain DNS configuration
3. Ensure nginx proxy is working

## Security Notes

- All clients share the same OAuth configuration but have isolated data
- Each client gets their own session storage and user database
- Data volumes are isolated between clients
- Consider firewall rules for production deployment

## Production Deployment

1. Update domain names in client scripts
2. Configure nginx for each client domain
3. Update Google OAuth redirect URIs
4. Set up SSL certificates for each domain
5. Configure firewall rules
6. Set up monitoring and backups