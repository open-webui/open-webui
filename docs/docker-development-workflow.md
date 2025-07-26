# Docker Development Workflow for mAI

## Overview
We use a three-tier Docker setup to optimize for both development speed and production safety.

## Configuration Files

### 1. `docker-compose.dev.yml` (Development - Hot Reload)
- **Purpose**: Fast development with instant code changes
- **Port**: 3001
- **Features**:
  - Volume mounts for backend/frontend code
  - Hot-reloading enabled (changes appear instantly)
  - No rebuild required for code changes
  - Separate data volume to avoid conflicts

### 2. `docker-compose-customization.yaml` (Staging/Production-like)
- **Purpose**: Test production builds before deployment
- **Port**: 3002
- **Features**:
  - Code baked into image (like production)
  - Requires rebuild for changes
  - Tests the actual Docker build process
  - Mimics production environment

### 3. `docker-compose.override.yml` (Personal Overrides)
- **Purpose**: Local developer preferences
- **Features**:
  - Git-ignored for personal settings
  - Automatically loaded by Docker Compose
  - Won't affect team members

## Workflows

### 🚀 Daily Development (Fastest)
```bash
# Start development environment with hot-reloading
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Make code changes - they appear instantly!
# No rebuild needed for Python/JS changes

# Stop when done
docker-compose -f docker-compose.dev.yml down
```

### 🧪 Testing Production Build
```bash
# When ready to test production-like build
docker-compose -f docker-compose-customization.yaml build --no-cache
docker-compose -f docker-compose-customization.yaml up -d

# Test at http://localhost:3002
```

### 🔄 Switching Between Environments
```bash
# Stop all containers first
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose-customization.yaml down

# Then start the one you need
```

## Best Practices

### For Development:
1. Use `docker-compose.dev.yml` for daily work
2. Code changes appear instantly (backend restarts automatically)
3. Check logs for errors: `docker logs -f open-webui-dev`
4. Database persists in `mai_dev_data` volume

### For Production Testing:
1. Always test with `docker-compose-customization.yaml` before pushing
2. This ensures your Dockerfile changes work correctly
3. Mimics the exact production build process

### Data Isolation:
- Dev data: `mai_dev_data` volume
- Staging data: `mai_customization_data` volume
- Production data: Separate volume on production server

## Common Commands

```bash
# Development
alias mai-dev='docker-compose -f docker-compose.dev.yml'
mai-dev up -d     # Start
mai-dev logs -f   # View logs
mai-dev down      # Stop
mai-dev restart   # Restart

# Staging/Production-like
alias mai-stage='docker-compose -f docker-compose-customization.yaml'
mai-stage build   # Build image
mai-stage up -d   # Start
mai-stage down    # Stop

# Check which is running
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

## Troubleshooting

### Changes not appearing in dev mode?
1. Check if file is volume-mounted in docker-compose.dev.yml
2. Check logs: `docker logs -f open-webui-dev`
3. For frontend changes, might need to refresh browser cache (Cmd+Shift+R)

### Port conflicts?
- Dev uses port 3001
- Staging uses port 3002
- Change in docker-compose.override.yml if needed

### Database issues?
- Dev and staging use separate volumes
- To reset dev DB: `docker volume rm mai_dev_data`
- To reset staging DB: `docker volume rm mai_customization_data`