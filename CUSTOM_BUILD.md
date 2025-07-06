# Custom Open WebUI Build for XYNTHORAI System

## Quick Start

1. **Clone and configure:**
```bash
git clone https://github.com/open-webui/open-webui.git xynthorai-open-webui
cd xynthorai-open-webui
git remote add upstream https://github.com/open-webui/open-webui.git
git fetch upstream
```

2. **Create custom branch:**
```bash
git checkout -b custom-dpl-integration
```

3. **Make changes and create patches:**
```bash
# Make changes in code
git add .
./scripts/create-patch.sh
```

4. **Build custom image:**
```bash
docker build -f Dockerfile.custom -t xynthorai-open-webui:custom .
```

## Project Structure

```
xynthorai-open-webui/
├── patches/                    # Your customizations as patches
│   ├── 001-xynthor-branding.patch
│   └── 002-dpl-integration.patch
├── custom-config/              # Additional configuration files
├── custom-scripts/             # Custom scripts
├── Dockerfile.custom           # Dockerfile for build
└── scripts/                    # Helper scripts
    ├── create-patch.sh         # Create new patches
    └── sync-upstream.sh        # Sync with upstream
```

## Patch Management

### Creating a new patch:
1. Make changes in code
2. Add files to git: `git add .`
3. Run: `./scripts/create-patch.sh`
4. Enter patch name and description

### Check patch:
```bash
git apply --check patches/001-xynthor-branding.patch
```

### Apply all patches:
```bash
for patch in patches/*.patch; do
    git apply "$patch"
done
```

## Sync with upstream

Run sync script:
```bash
./scripts/sync-upstream.sh
```

Script will automatically:
- Create backup branch
- Try to merge changes from upstream
- Check patches compatibility
- Report conflicts

## Docker Integration

Update docker-compose.yml:
```yaml
open-webui:
  build:
    context: ./xynthorai-open-webui
    dockerfile: Dockerfile.custom
  image: xynthorai-open-webui:custom
  # ... rest of configuration
```

## CI/CD

GitHub Actions automatically:
- Checks new upstream versions weekly
- Tests patches for compatibility
- Builds and publishes Docker images
- Creates PR when updates available

## Update Security

1. **Staging environment**: Test updates before production
2. **Versioning**: Each build has unique tag
3. **Rollback**: Keep previous image versions
4. **Monitoring**: Track errors after updates

## Customization Examples

### Branding:
- Logo: `patches/001-xynthor-branding.patch`
- Colors: create patch for `tailwind.config.js`
- Texts: modify components in `src/lib/components`

### XYNTHORAI Integration:
- API endpoints: `patches/002-dpl-integration.patch`
- Middleware hooks: add to `backend/apps/webui`
- Policy checking: integrate in `backend/apps/openai`

## Troubleshooting

### Patch won't apply:
1. Check base commit
2. Update patch according to new changes
3. Split large patch into smaller ones

### Merge conflicts:
1. Use backup branch
2. Resolve conflicts manually
3. Create new patch

### Build failures:
1. Check dependencies
2. Clear Docker cache: `docker builder prune`
3. Use `--no-cache` flag