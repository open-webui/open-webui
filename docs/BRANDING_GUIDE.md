# XYNTHOR AI Branding Guide for Open WebUI

## Overview
This guide explains how to apply custom XYNTHOR AI branding to Open WebUI, including logo replacement, text changes, and complete removal of Open WebUI references.

## Branding Components

### 1. Logo Files
Located in `/xynthorai-open-webui/static-assets/`:
- `logo.png` - Main logo (fingerprint design)
- `xynthor-logo.png` - XYNTHOR logo
- `xynthor-favicon.ico` - XYNTHOR favicon

### 2. Text Replacements
- "Open WebUI" → "XYNTHOR AI"
- Removes "(Open WebUI)" suffix from titles
- Updates all UI text references

### 3. Asset Locations
The branding replaces files in these locations:
- `/app/static/` - Static assets
- `/app/build/` - Built frontend files
- `/app/build/static/` - Frontend static assets
- `/app/backend/open_webui/static/` - Backend static assets

## Implementation Methods

### Method 1: Docker Build with Local Assets (Recommended)

```bash
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui

# Build with comprehensive branding
docker build -f Dockerfile.xynthor-v6 -t xynthorai-open-webui:xynthor-v6 .

# Update docker-compose.yml
cd ..
sed -i '' 's/image: xynthorai-open-webui:.*/image: xynthorai-open-webui:xynthor-v6/' docker-compose.yml

# Restart service
docker-compose restart open-webui
```

### Method 2: Environment Variables Only (Limited)

```yaml
environment:
  - WEBUI_NAME=XYNTHOR AI
  - WEBUI_BRAND_NAME=XYNTHOR AI
  - WEBUI_BRAND_LOGO_URL=https://your-domain.com/logo.png
  - WEBUI_PRIMARY_COLOR=#f97316
  - WEBUI_FAVICON_URL=https://your-domain.com/favicon.ico
```

**Note**: Environment variables alone don't replace all branding elements.

### Method 3: Volume Mounts (Quick Testing)

```yaml
volumes:
  - ./static-assets/logo.png:/app/static/logo.png
  - ./static-assets/logo.png:/app/static/splash.png
  - ./static-assets/xynthor-favicon.ico:/app/static/favicon.ico
```

## The Branding Script

The `apply-branding-local.sh` script performs:

1. **HTML Patching**
   - Updates favicon references
   - Changes meta content
   - Replaces title tags

2. **JavaScript Patching**
   - Finds and replaces all "Open WebUI" text
   - Updates logo references
   - Removes "(Open WebUI)" suffixes
   - Patches favicon and splash references

3. **CSS Patching**
   - Updates logo references in stylesheets

4. **Asset Copying**
   - Copies logo to multiple locations
   - Ensures assets are accessible

## Dockerfile Breakdown

### Dockerfile.xynthor-v3 Structure

```dockerfile
# Base image
FROM ghcr.io/open-webui/open-webui:latest

# Install tools
USER root
RUN apt-get update && apt-get install -y sed

# Copy assets to all required locations
COPY static-assets/logo.png /app/static/logo.png
COPY static-assets/logo.png /app/static/splash.png
# ... more asset copies ...

# Apply branding script
COPY apply-branding-local.sh /app/apply-branding.sh
RUN chmod +x /app/apply-branding.sh
RUN /app/apply-branding.sh

# Set environment variables
ENV WEBUI_NAME="XYNTHOR AI"
ENV WEBUI_BRAND_NAME="XYNTHOR AI"
```

## Troubleshooting Branding Issues

### Issue: Title shows "XYNTHOR AI (Open WebUI)"

**Solution**: The script includes aggressive pattern matching:
```bash
sed -i 's/XYNTHOR AI (Open WebUI)/XYNTHOR AI/g' "$file"
sed -i 's/ (Open WebUI)//g' "$file"
sed -i 's/\(Open WebUI\)//g' "$file"
```

### Issue: Old logo still appears

**Locations to check**:
1. Sidebar icon: `/static/favicon.png`
2. Splash screen: `/static/splash.png`
3. Browser favicon: `/favicon.ico`

**Solution**: Clear browser cache (Ctrl+F5 or Cmd+Shift+R)

### Issue: Model profile images show broken `/logo.png` path

**Problem**: Model list images use incorrect path `/logo.png` instead of `/static/logo.png`, causing 404 errors for non-admin users.

**Solution**: Use `Dockerfile.xynthor-v6` or later which includes the `fix-static-paths.sh` script that corrects these paths:
```bash
# The fix converts paths like:
src="/logo.png" → src="/static/logo.png"
```

### Issue: Some references remain

**Debug steps**:
```bash
# Check inside container
docker exec -it xynthorai-open-webui bash

# List replaced files
ls -la /app/static/
ls -la /app/build/static/

# Search for remaining references
find /app/build -name "*.js" -exec grep -l "Open WebUI" {} \;
```

## Adding New Branding Assets

1. **Add asset to static-assets/**
   ```bash
   cp your-logo.png xynthorai-open-webui/static-assets/
   ```

2. **Update Dockerfile**
   ```dockerfile
   COPY static-assets/your-logo.png /app/static/your-logo.png
   ```

3. **Update branding script** if needed
   ```bash
   sed -i 's|old-reference|new-reference|g' "$file"
   ```

4. **Rebuild image**
   ```bash
   docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v4 .
   ```

## Best Practices

1. **Always backup before updates**
   ```bash
   docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:backup-$(date +%Y%m%d)
   ```

2. **Test branding locally**
   ```bash
   docker run -p 8081:8080 xynthorai-open-webui:xynthor-v3
   ```

3. **Use high-quality assets**
   - Logo: PNG with transparency, min 512x512px
   - Favicon: ICO format with multiple sizes

4. **Version your branding**
   ```bash
   docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:branding-v1.0
   ```

## Advanced Customization

### Custom CSS
Add to branding script:
```bash
echo "
.sidebar-logo { filter: brightness(1.2); }
.splash-logo { max-width: 200px; }
" >> /app/build/static/custom.css
```

### Theme Colors
Modify in docker-compose.yml:
```yaml
- WEBUI_PRIMARY_COLOR=#f97316  # Orange
- WEBUI_SECONDARY_COLOR=#64748b # Gray
```

### Additional Text Replacements
Add to `apply-branding-local.sh`:
```bash
# Custom replacements
sed -i 's/Specific Text/Your Text/g' "$file"
```

## Maintenance

### Updating Base Image
```bash
# Pull latest
docker pull ghcr.io/open-webui/open-webui:latest

# Rebuild with branding
docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 . --no-cache
```

### Checking Applied Branding
```bash
# Inside container
docker exec xynthorai-open-webui cat /app/build/index.html | grep -i "xynthor"
docker exec xynthorai-open-webui find /app/build -name "*.js" -exec grep -l "Open WebUI" {} \; | wc -l
```

## Quick Reference

```bash
# Build
docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 .

# Deploy
docker-compose up -d open-webui

# Verify
curl -s http://localhost:8080 | grep -i "xynthor"

# Rollback
docker tag xynthorai-open-webui:backup-20240627 xynthorai-open-webui:xynthor-v3
docker-compose restart open-webui
```

## Support

For issues with branding:
1. Check container logs: `docker-compose logs open-webui`
2. Verify files are copied: `docker exec xynthorai-open-webui ls -la /app/static/`
3. Clear browser cache and cookies
4. Rebuild with `--no-cache` flag