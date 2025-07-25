# Development Guide

This guide covers development workflows, customizations, and maintaining mAI.

## Branch Strategy

### Core Rules
- **ALWAYS** work on `customization` branch (never commit to main)
- **ALWAYS** create backups before asset modifications
- **Main branch**: Keep clean for upstream merges from Open WebUI
- **Feature branches**: Create from `customization` for specific improvements

### Branch Commands
```bash
# Switch to customization branch
git checkout customization

# Create feature branch
git checkout -b feature/new-theme customization

# Merge feature to customization
git checkout customization
git merge feature/new-theme
```

## Development Workflow

### 1. Asset Modifications
```bash
# Create backup
cp -r static/static customization-backup/static-$(date +%Y%m%d)

# Make changes to:
# - Logo files: static/static/ and backend/open_webui/static/
# - CSS: static/custom.css
# - Themes: static/themes/
```

### 3. Commit Guidelines

Use proper prefixes:
- `brand:` - Logo, branding changes
- `theme:` - Color schemes, CSS modifications
- `ui:` - User interface, layout changes
- `assets:` - Static assets, images, icons
- `i18n:` - Translations
- `fix:` - Bug fixes
- `feat:` - New features
- `docs:` - Documentation updates

Example:
```bash
git add .
git commit -m "brand: Update logo assets and favicon"
```

## Development Commands

### Build & Test
```bash
# Install dependencies
npm install

# Build frontend
npm run build

# Type checking
npm run check

# Linting
npm run lint
```

### Docker Development
```bash
# Build development image
docker build -t mai-dev:latest .

# Run with local Ollama
docker run -d -p 3002:8080 --name mai-dev mai-dev:latest
```

## File Locations

### Frontend
- Components: `src/lib/components/`
- Stores: `src/lib/stores/`
- Translations: `src/lib/i18n/locales/`

### Backend
- API Routes: `backend/open_webui/routers/`
- Models: `backend/open_webui/models/`
- Utils: `backend/open_webui/utils/`

### Assets
- Logos: `static/static/`
- Themes: `static/themes/`
- Custom CSS: `static/custom.css`