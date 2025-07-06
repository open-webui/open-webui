# Open WebUI Custom - XYNTHOR AI Edition

This is a customized version of Open WebUI with XYNTHOR AI branding and XYNTHORAI(Data Policy Layer) integration.

## Features

- **Complete XYNTHOR AI Branding**: Custom logo, favicon, and all text references updated
- **XYNTHORAIMiddleware Integration**: Built-in support for policy verification and content filtering
- **Local Asset Management**: All branding assets stored locally for full control
- **Aggressive Branding Replacement**: Removes all "Open WebUI" references including "(Open WebUI)" suffixes

## Quick Start

### Building the Custom Image

```bash
cd /Users/admin_pro/_Web/xynthorai-system/xynthorai-open-webui

# Build with full branding
docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 .
```

### Running with Docker Compose

The image is already integrated into the main XYNTHORAIsystem:

```bash
cd /Users/admin_pro/_Web/xynthorai-system
docker-compose up -d open-webui
```

## Branding Components

### Static Assets

Located in `static-assets/`:
- `logo.png` - Main logo (fingerprint design)
- `xynthor-logo.png` - XYNTHOR logo
- `xynthor-favicon.ico` - XYNTHOR favicon

### Branding Script

`apply-branding-local.sh` performs:
- Text replacement in HTML, JS, CSS files
- Logo and favicon replacement
- Removal of "(Open WebUI)" suffixes
- Asset copying to all required locations

## Available Dockerfiles

1. **Dockerfile.simple** - Basic customization with environment variables
2. **Dockerfile.local-assets** - Includes local branding assets
3. **Dockerfile.xynthor-v3** - Advanced branding with aggressive replacement (recommended)

## Updating

### Quick Update

```bash
./update.sh
```

### Manual Update

```bash
# Pull latest base
docker pull ghcr.io/open-webui/open-webui:latest

# Rebuild with branding
docker build -f Dockerfile.xynthor-v3 -t xynthorai-open-webui:xynthor-v3 . --no-cache

# Restart
cd ..
docker-compose restart open-webui
```

## Documentation

- [Custom Build and Update Guide](./CUSTOM_BUILD_AND_UPDATE.md) - Detailed build instructions
- [Branding Guide](./BRANDING_GUIDE.md) - Complete branding customization guide
- [Security](./SECURITY.md) - Security considerations
- [Contributing](./CONTRIBUTING.md) - How to contribute

## Troubleshooting

### Branding Not Applied

1. Clear browser cache (Ctrl+F5 or Cmd+Shift+R)
2. Check container logs: `docker-compose logs open-webui`
3. Verify assets: `docker exec xynthorai-open-webui ls -la /app/static/`

### Title Shows "(Open WebUI)"

The xynthor-v3 image includes aggressive pattern matching to remove this. If it persists:

```bash
# Check inside container
docker exec -it xynthorai-open-webui bash
grep -r "Open WebUI" /app/build/
```

## Project Workflow

[![](https://mermaid.ink/img/pako:eNq1k01rAjEQhv_KkFNLFe1N9iAUevFSRVl6Cci4Gd1ANtlmsmtF_O_N7iqtHxR76ClhMu87zwyZvcicIpEIpo-KbEavGjceC2lL9EFnukQbIGXygNye5y9TY7DAZTpZLsjXXVYXg3dapRM4hh9mu5A7-3hTfSXtAtJK21Tsj8dPl3USmJZkGVbebWNKD2rNOjAYl6HJHYdkNBwNpb3U9aNZvzFNYE6h8tFiSyZzBUGJG4K1dwVwTSYQrCptlLRvLt5dA5i2la5Ruk51Ux0VKQjuxPVbAwuyiuFlNgHfzJ5DoxtgqQf1813gnZRLZ5lAYcD7WT1lpGtiQKug9C4jZrrp-Fd-1-Y1bdzo4dvnZDLz7lPHyj8sOgfg4x84E7RTuEaZt8yRZqtDfgT_rwG2u3Dv_ERPFOQL1Cqu2F5aAClCTgVJkcSrojVWJkgh7SGmYhXcYmczkQRfUU9UZfQ4baRI1miYDl_QqlPg?type=png)](https://mermaid.live/edit#pako:eNq1k01rAjEQhv_KkFNLFe1N9iAUevFSRVl6Cci4Gd1ANtlmsmtF_O_N7iqtHxR76ClhMu87zwyZvcicIpEIpo-KbEavGjceC2lL9EFnukQbIGXygNye5y9TY7DAZTpZLsjXXVYXg3dapRM4hh9mu5A7-3hTfSXtAtJK21Tsj8dPl3USmJZkGVbebWNKD2rNOjAYl6HJHYdkNBwNpb3U9aNZvzFNYE6h8tFiSyZzBUGJG4K1dwVwTSYQrCptlLRvLt5dA5i2la5Ruk51Ux0VKQjuxPVbAwuyiuFlNgHfzJ5DoxtgqQf1813gnZRLZ5lAYcD7WT1lpGtiQKug9C4jZrrp-Fd-1-Y1bdzo4dvnZDLz7lPHyj8sOgfg4x84E7RTuEaZt8yRZqtDfgT_rwG2u3Dv_ERPFOQL1Cqu2F5aAClCTgVJkcSrojVWJkgh7SGmYhXcYmczkQRfUU9UZfQ4baRI1miYDl_QqlPg)

## Support

- Fork Repository: https://github.com/ivanplzv/open-webui
- Upstream: https://github.com/open-webui/open-webui
- XYNTHORAI System: Internal documentation
