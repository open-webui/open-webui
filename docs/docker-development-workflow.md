# Docker Development Workflow for mAI

## Overview
We use a **dual environment** Docker setup with **separate API keys** to ensure complete isolation between development and production-like testing.

## ⚡ Key Principle: Environment Files First!
**CRITICAL**: Always generate environment files **BEFORE** building Docker containers.

## Configuration Files

### 1. `docker-compose.dev.yml` (Development - Hot Reload)
- **Purpose**: Fast development with instant code changes
- **Port**: 3001
- **Env File**: `.env.dev` (separate API key)
- **Database**: `mai_dev_data` (isolated)
- **Features**:
  - Volume mounts for backend/frontend code
  - Hot-reloading enabled (changes appear instantly)
  - No rebuild required for code changes
  - Complete isolation from production

### 2. `docker-compose-customization.yaml` (Staging/Production-like)
- **Purpose**: Test production builds before deployment
- **Port**: 3002
- **Env File**: `.env` (production API key)
- **Database**: `mai_customization_data` (isolated)
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

### 🚀 Development Setup (First Time)
```bash
# Step 1: Generate development environment file
python3 generate_client_env_dev.py
# This creates .env.dev with separate OpenRouter API key

# Step 2: Build development container
docker-compose -f docker-compose.dev.yml build

# Step 3: Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Step 4: Access at http://localhost:3001
# Create first user (becomes admin automatically)
```

### 🔄 Daily Development (After Setup)
```bash
# Start development environment
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

### 🔄 Environment Comparison

| Aspect | Development (3001) | Production-like (3002) |
|--------|-------------------|------------------------|
| **Env File** | `.env.dev` | `.env` |
| **API Key** | Separate dev key | Production key |
| **External User** | `dev_mai_client_xxx` | `mai_client_xxx` |
| **Database** | `mai_dev_data` | `mai_customization_data` |
| **Hot Reload** | ✅ Yes | ❌ No |
| **Code Access** | Volume mounted | Baked into image |
| **Rebuild Required** | ❌ Never | ✅ Always |

## Best Practices

### ⚠️ CRITICAL Setup Order:
1. **Generate environment file FIRST**: `python3 generate_client_env_dev.py`
2. **Then build container**: `docker-compose -f docker-compose.dev.yml build`
3. **Never skip step 1** - container needs `.env.dev` to build

### For Development:
1. Use `docker-compose.dev.yml` for daily work
2. Code changes appear instantly (backend restarts automatically)
3. Check logs for errors: `docker logs -f open-webui-dev`
4. Database persists in `mai_dev_data` volume
5. Safe to experiment - completely isolated from production

### For Production Testing:
1. Always test with `docker-compose-customization.yaml` before pushing
2. This ensures your Dockerfile changes work correctly
3. Mimics the exact production build process
4. Uses production API key and settings

### Complete Environment Isolation:
- **API Keys**: Separate OpenRouter keys (no quota conflicts)
- **Databases**: `mai_dev_data` vs `mai_customization_data` 
- **External Users**: `dev_` prefix prevents conflicts
- **Organizations**: Clearly marked with "(DEV)" suffix
- **Data Safety**: Dev experiments won't affect production

## Common Commands

```bash
# Development Environment
alias mai-dev='docker-compose -f docker-compose.dev.yml'

# FIRST TIME SETUP
python3 generate_client_env_dev.py  # Generate .env.dev
mai-dev build                       # Build with environment
mai-dev up -d                       # Start

# DAILY USAGE
mai-dev up -d     # Start
mai-dev logs -f   # View logs
mai-dev down      # Stop
mai-dev restart   # Restart

# Production-like Environment
alias mai-stage='docker-compose -f docker-compose-customization.yaml'
mai-stage build   # Build image
mai-stage up -d   # Start
mai-stage down    # Stop

# Check which is running
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

## Troubleshooting

### Error: ".env.dev not found"
```bash
# SOLUTION: Generate environment file first
python3 generate_client_env_dev.py
# Then build: docker-compose -f docker-compose.dev.yml build
```

### Changes not appearing in dev mode?
1. Ensure hot-reload is working: `docker logs -f open-webui-dev`
2. Look for "Detected file change... Reloading..." in logs
3. For frontend changes, refresh browser cache (Cmd+Shift+R)
4. Check file is volume-mounted in docker-compose.dev.yml

### "Background sync" error in logs?
- **Non-critical**: Core functionality works normally
- Fixed in latest commits with background_sync.py stub

### API key conflicts between environments?
- **Not possible**: Each environment uses separate API keys
- Dev: Uses key from `.env.dev` (generated separately)
- Production: Uses key from `.env` (existing setup)

### Database conflicts?
- **Not possible**: Complete database isolation
- Dev: `mai_dev_data` volume 
- Production: `mai_customization_data` volume
- To reset dev DB: `docker volume rm mai_dev_data`
- To reset production DB: `docker volume rm mai_customization_data`

### Port conflicts?
- Dev: `localhost:3001`
- Production-like: `localhost:3002`
- Both can run simultaneously without conflicts