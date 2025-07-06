# Open WebUI Custom Update Log

## Version History

### v1.0.3 - XYNTHOR Branding V3 (2024-06-27)
- **Image**: `xynthorai-open-webui:xynthor-v3`
- **Changes**:
  - Implemented aggressive text replacement to remove all "(Open WebUI)" suffixes
  - Updated to use `logo.png` from static-assets instead of xynthor-logo.png
  - Added comprehensive JavaScript, CSS, and Python file patching
  - Improved branding script with additional pattern matching
  - Copies assets to `/app/build/static/` for better coverage
- **Known Issues**: All resolved

### v1.0.2 - XYNTHOR Branding V2 (2024-06-27)
- **Image**: `xynthorai-open-webui:xynthor-v2`
- **Changes**:
  - Added local asset management
  - Created `apply-branding-local.sh` script
  - Replaced logos and favicons with local files
- **Known Issues**:
  - Title still showing "(Open WebUI)" suffix
  - Some logo references not updated

### v1.0.1 - Simple Build (2024-06-27)
- **Image**: `xynthorai-open-webui:simple`
- **Changes**:
  - Basic environment variable configuration
  - XynthorAI middleware integration
  - Initial XYNTHOR branding via env vars
- **Known Issues**:
  - Limited branding coverage

### v1.0.0 - Initial Custom Build (2024-06-27)
- **Image**: `xynthorai-open-webui:patched`
- **Changes**:
  - Applied initial branding patches
  - Fixed corrupt patch issues
  - Basic customization

## Update Procedures

### Standard Update
```bash
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui
./update.sh
```

### Manual Update with Backup
```bash
# Create backup
docker tag xynthorai-open-webui:xynthor-v3 xynthorai-open-webui:backup-$(date +%Y%m%d-%H%M%S)

# Pull latest base
docker pull ghcr.io/open-webui/open-webui:latest

# Rebuild
docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 . --no-cache

# Deploy
cd ..
docker-compose restart open-webui
```

## Branding Assets

### Current Assets (v1.0.3)
- `static-assets/logo.png` - Main logo (fingerprint design)
- `static-assets/xynthor-logo.png` - XYNTHOR logo (deprecated)
- `static-assets/xynthor-favicon.ico` - XYNTHOR favicon

### Asset Locations After Build
- `/app/static/` - Static assets
- `/app/build/` - Frontend build
- `/app/build/static/` - Frontend static
- `/app/backend/open_webui/static/` - Backend static

## Testing Checklist

After each update, verify:
- [ ] Title shows "XYNTHOR AI" (no suffix)
- [ ] Favicon displays correctly
- [ ] Sidebar logo is updated
- [ ] Splash screen shows custom logo
- [ ] No "Open WebUI" text remains
- [ ] XynthorAI middleware integration works

## Rollback Procedures

### Quick Rollback
```bash
# List backups
docker images | grep xynthorai-open-webui | grep backup

# Restore
docker tag xynthorai-open-webui:backup-20240627-153045 xynthorai-open-webui:xynthor-v3
docker-compose restart open-webui
```

### From Saved Image
```bash
docker load < backup-openwebui-20240627.tar.gz
docker-compose up -d open-webui
```

## Notes for Future Updates

1. Always test branding in isolated container first
2. Clear browser cache after updates
3. Check JavaScript console for errors
4. Monitor container logs during startup
5. Keep backup of working images
6. Document any new branding requirements

## Upstream Sync

To check for upstream updates:
```bash
# Add upstream if not exists
git remote add upstream https://github.com/open-webui/open-webui.git

# Fetch updates
git fetch upstream

# Check changes
git log upstream/main --oneline -10
```

## Contact

For issues or questions about customization:
- Check `/xynthorai-open-webui/docs/` directory
- Review container logs: `docker-compose logs open-webui`
- Test in development environment first