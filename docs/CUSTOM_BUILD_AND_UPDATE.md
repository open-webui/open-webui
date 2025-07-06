# Custom Build and Update Guide

## Overview
This document describes how to build and maintain a customized version of Open WebUI with XYNTHORAI integration and XYNTHOR branding.

## Current Setup

### Docker Image
- **Current Image**: `xynthorai-open-webui:xynthor-final`
- **Base**: `ghcr.io/open-webui/open-webui:latest`
- **Dockerfiles**: 
  - `Dockerfile.simple` - Basic customization
  - `Dockerfile.local-assets` - With local branding assets
  - `Dockerfile.xynthor-v3` - Advanced branding with aggressive replacement
  - `Dockerfile.xynthor-v4` - Version with symlinks and startup script
  - `Dockerfile.xynthor-final` - Final comprehensive version (CURRENT)
- **Integration**: Already configured in main `docker-compose.yml`

### Repository Structure
```
xynthorai-open-webui/
├── patches/                    # Customization patches
│   └── 001-xynthor-branding.patch
├── static-assets/             # Local branding assets
│   ├── logo.png              # Custom logo (fingerprint design)
│   ├── xynthor-logo.png      # XYNTHOR logo
│   └── xynthor-favicon.ico   # XYNTHOR favicon
├── custom-config/             # Additional configuration files
├── docs/                      # Documentation
├── Dockerfile.simple          # Basic dockerfile
├── Dockerfile.local-assets    # With local assets
├── Dockerfile.xynthor-v3      # Advanced branding
├── Dockerfile.xynthor-v4      # With symlinks
├── Dockerfile.xynthor-final   # Comprehensive version (CURRENT)
├── apply-branding-local.sh    # Branding script
├── update.sh                  # Update script
└── docker-compose.custom.yml  # Standalone testing
```

### Fork Configuration
- **Your Fork**: `git@github-ivan:ivanplzv/open-webui.git` (origin)
- **Upstream**: `https://github.com/open-webui/open-webui.git` (push disabled)
- **Branch**: `custom-dpl-integration`

## Building the Custom Image

### Quick Build
```bash
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui

# Basic build
docker build -f Dockerfile.simple -t xynthorai-open-webui:simple .

# With local branding assets (recommended)
docker build -f Dockerfile.xynthor-final -t xynthorai-open-webui:xynthor-final .
```

### What's Included
- XYNTHOR AI branding:
  - Complete text replacement (removes "(Open WebUI)" suffix)
  - Custom logo and favicon from local assets
  - JavaScript, CSS, and Python file patching
- XynthorAI middleware integration settings
- Custom configuration directory
- Local asset replacement:
  - Sidebar logo
  - Splash screen logo
  - Favicon
  - All logo references

## Update Process

### Automated Update
```bash
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui
./update.sh

# Then restart the service
cd ..
docker-compose restart open-webui
```

### Manual Update Steps
1. **Pull latest base image**
   ```bash
   docker pull ghcr.io/open-webui/open-webui:latest
   ```

2. **Create backup**
   ```bash
   docker tag xynthorai-open-webui:simple xynthorai-open-webui:backup-$(date +%Y%m%d)
   ```

3. **Rebuild custom image**
   ```bash
   # For advanced branding (recommended)
   docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 . --no-cache
   
   # Update docker-compose.yml to use new image
   sed -i 's/image: xynthorai-open-webui:.*/image: xynthorai-open-webui:xynthor-v3/' ../docker-compose.yml
   ```

4. **Restart service**
   ```bash
   cd /Users/admin_pro/_Web/xynthorai-system
   docker-compose restart open-webui
   ```

## Version Management

### Tagging Scheme
```bash
# Production versions
docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:v1.0.3

# Date-based tags
docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:2024.06.27

# Backup tags (automatic)
docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:backup-20240627-153045

# Branding versions
docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:latest
```

### Checking Current Version
```bash
# See when image was built
docker inspect xynthorai-open-webui:simple --format '{{.Created}}'

# List all versions
docker images | grep xynthorai-open-webui
```

## Rollback Procedure

### If Update Fails
```bash
# List available backups
docker images | grep xynthorai-open-webui | grep backup

# Restore previous version
docker tag xynthorai-open-webui:backup-20240627 xynthorai-open-webui:simple

# Restart with old version
docker-compose restart open-webui
```

### Complete Rollback
```bash
# Stop service
docker-compose stop open-webui

# Restore from backup file (if saved)
docker load < backup-openwebui-20240627.tar.gz

# Start service
docker-compose up -d open-webui
```

## Customization Options

### Environment Variables (Working)
- `WEBUI_NAME=XYNTHOR AI`
- `WEBUI_BRAND_NAME=XYNTHOR AI`
- `APP_NAME=XYNTHOR AI`
- `XYNTHORAI_ENABLED=true`
- `XYNTHORAI_MIDDLEWARE_URL=http://xynthorai-middleware:3000`
- `WEBUI_PRIMARY_COLOR=#f97316`

### Patches (For deeper changes)
1. Create changes in code
2. Generate patch: `git diff > patches/002-new-feature.patch`
3. Rebuild image
4. Test thoroughly

### Volume Mounts (For quick changes)
```yaml
volumes:
  - ./static-assets/logo.png:/app/backend/static/logo.png
  - ./static-assets/logo.png:/app/static/splash.png
  - ./static-assets/xynthor-favicon.ico:/app/static/favicon.ico
  - ./custom-styles.css:/app/backend/static/custom.css
```

## Monitoring Updates

### Check for New Releases
```bash
# Via GitHub API
curl -s https://api.github.com/repos/open-webui/open-webui/releases/latest | jq -r '.tag_name'

# Via Docker Hub
docker pull ghcr.io/open-webui/open-webui:latest
docker inspect ghcr.io/open-webui/open-webui:latest | grep -i version
```

### Security Updates
- Subscribe to https://github.com/open-webui/open-webui/releases
- Check for CVEs: `docker scout cves xynthorai-open-webui:simple`
- Update immediately for security patches

## Best Practices

1. **Test Before Production**
   ```bash
   docker run -p 8081:8080 xynthorai-open-webui:simple
   ```

2. **Document Changes**
   - Keep UPDATE_LOG.md with version history
   - Note what customizations were applied

3. **Clean Up Old Images**
   ```bash
   # Remove old backups (keep last 3)
   docker images | grep backup | sort -r | tail -n +4 | awk '{print $3}' | xargs docker rmi
   ```

4. **Backup Before Major Updates**
   ```bash
   docker save xynthorai-open-webui:simple | gzip > backup-$(date +%Y%m%d).tar.gz
   ```

## Troubleshooting

### Build Fails
- Check Docker daemon is running
- Ensure enough disk space
- Try with `--no-cache` flag
- Check network connectivity

### Update Issues
- Verify base image is accessible
- Check for breaking changes in release notes
- Test in isolated environment first

### Customizations Not Visible
- Clear browser cache (Ctrl+F5 or Cmd+Shift+R)
- Check environment variables are set
- Verify volume mounts are correct
- Check container logs: `docker-compose logs open-webui`
- For logo issues:
  - Check /static/favicon.png is replaced
  - Check /static/splash.png is replaced
  - Verify JavaScript files are patched
- For title issues:
  - Look for "(Open WebUI)" suffix
  - Check aggressive replacement patterns

## Quick Reference

```bash
# Build with branding
docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 .

# Update
./update.sh

# Check version
docker images xynthorai-open-webui

# Restart
docker-compose restart open-webui

# Logs
docker-compose logs -f open-webui

# Check branding applied
docker exec xynthorai-open-webui ls -la /app/static/

# Rollback
docker tag xynthorai-open-webui:backup-YYYYMMDD xynthorai-open-webui:xynthor-v3
```

## Support

- Fork Repository: https://github.com/ivanplzv/open-webui
- Upstream Issues: https://github.com/open-webui/open-webui/issues
- Documentation: This file and others in `/docs` directory