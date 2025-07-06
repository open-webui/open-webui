# Usage Guide for Custom Open WebUI

## Build Status

✅ **Simple Docker image built successfully**: `xynthorai-open-webui:simple`

## Two Approaches Available

### 1. Simple Approach (Recommended for Start)
Uses environment variables and runtime configuration:

```bash
# Build
docker build -f Dockerfile.simple -t xynthorai-open-webui:simple .

# Run
docker run -d \
  -p 8080:8080 \
  -v open-webui:/app/backend/data \
  --name xynthorai-open-webui \
  xynthorai-open-webui:simple
```

### 2. Full Custom Build (For Deep Customization)
Applies patches during build:

```bash
# Fix the long build time by using cache
docker build -f Dockerfile.custom -t xynthorai-open-webui:custom . --progress=plain
```

## Using in Docker Compose

Update your main `docker-compose.yml`:

```yaml
open-webui:
  # Use simple image
  image: xynthorai-open-webui:simple
  # Or use custom build
  # build:
  #   context: ./xynthorai-open-webui
  #   dockerfile: Dockerfile.simple
```

## Environment Variables for Customization

The official Open WebUI supports these in the community edition:
- `WEBUI_NAME` - Changes the app name in some places
- `WEBUI_URL` - Base URL configuration
- `ENABLE_OAUTH_SIGNUP` - OAuth settings
- Various API configurations

For full branding (logo, favicon, colors), you need either:
1. Enterprise license
2. Apply patches during build (Dockerfile.custom)
3. Mount custom files via volumes

## Current Customizations

### What's Working:
- ✅ XynthorAI middleware integration via environment variables
- ✅ OAuth/OIDC with Keycloak
- ✅ Custom docker image with your patches included

### What Needs Patches:
- ❌ Favicon changes (requires patch 001-xynthor-branding.patch)
- ❌ Logo replacement in navbar
- ❌ Color scheme changes
- ❌ Deep UI customizations

## Next Steps

1. **Test Simple Image**:
   ```bash
   docker run -p 8081:8080 xynthorai-open-webui:simple
   # Visit http://localhost:8081
   ```

2. **Apply to Main System**:
   - Update `/Users/admin_pro/_Web/xynthorai-system/docker-compose.yml`
   - Change image to `xynthorai-open-webui:simple`

3. **For Full Customization**:
   - Fix patches to apply cleanly
   - Use Dockerfile.custom for build
   - Consider mounting static files as volumes

## Troubleshooting

### Build Takes Too Long
- Use `--progress=plain` to see what's happening
- Consider using buildx with cache: `docker buildx build --cache-from type=gha`
- Split into smaller stages

### Patches Don't Apply
- Check patch format (must end with newline)
- Verify base commit matches
- Use `git apply --check` to test

### Customizations Not Showing
- Clear browser cache
- Check if enterprise features
- Verify environment variables are set