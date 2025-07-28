# mAI Development Environment - Hot Reload Guide

## Overview

This guide describes the two-container development architecture that enables true hot reload for both frontend and backend components of the mAI application.

## Architecture

### Previous Single-Container Problem
- Frontend was built during Docker image creation (`npm run build`)
- Only backend had hot reload via uvicorn --reload
- Frontend changes required full container rebuild with `--no-cache`
- Development workflow was slow and inefficient

### New Two-Container Solution
- **Frontend Container**: Runs Vite dev server with Hot Module Replacement (HMR)
- **Backend Container**: Runs FastAPI with uvicorn --reload
- Both containers have independent hot reload capabilities
- Cross-container communication via Docker networking

## Development Workflow

### Quick Start
```bash
# Start development environment
./dev-hot-reload.sh up

# Access applications
# Frontend (Vite HMR): http://localhost:5173
# Backend API:         http://localhost:8080
# Health Check:        http://localhost:8080/health

# Stop environment
./dev-hot-reload.sh down
```

### Available Commands
```bash
./dev-hot-reload.sh [COMMAND]

Commands:
  up, start     Start the development environment
  down, stop    Stop the development environment
  restart       Restart the development environment
  logs          Show logs from all services
  logs-fe       Show frontend logs only
  logs-be       Show backend logs only
  build         Rebuild containers without cache
  clean         Stop containers and remove volumes
  status        Show container status
  shell-fe      Open shell in frontend container
  shell-be      Open shell in backend container
  help          Show help message
```

## Container Architecture

### Frontend Container (mai-frontend-dev)
- **Base Image**: node:22-alpine3.20
- **Dockerfile**: `Dockerfile.frontend.dev`
- **Port**: 5173 (Vite dev server)
- **Features**:
  - Vite dev server with HMR
  - Live file watching for `src/`, `static/`, config files
  - API proxy to backend container
  - Hot Module Replacement for instant UI updates

### Backend Container (mai-backend-dev)
- **Base Image**: python:3.11-slim-bookworm
- **Dockerfile**: `Dockerfile.backend.dev`
- **Port**: 8080 (FastAPI with uvicorn)
- **Features**:
  - uvicorn with --reload flag
  - Live file watching for `backend/` directory
  - SQLite database persistence
  - Full OpenRouter integration

## File Structure

```
mAI/
├── Dockerfile.frontend.dev          # Frontend development container
├── Dockerfile.backend.dev           # Backend development container
├── docker-compose.dev.yml           # Two-container orchestration
├── dev-hot-reload.sh                # Development management script
├── vite.config.ts                   # Updated with Docker proxy config
└── package.json                     # Added dev:docker script
```

## Configuration Files

### docker-compose.dev.yml
```yaml
services:
  frontend-dev:
    # Vite dev server with HMR
    ports: ["5173:5173"]
    environment:
      - VITE_HOST=0.0.0.0
      - DOCKER_DEV=true
    
  backend-dev:
    # FastAPI with hot reload
    ports: ["8080:8080"]
    environment:
      - CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:3001
```

### vite.config.ts
```typescript
server: {
  host: process.env.VITE_HOST || 'localhost',
  port: 5173,
  proxy: process.env.DOCKER_DEV === 'true' ? {
    '/api': {
      target: 'http://backend-dev:8080',
      changeOrigin: true
    }
  } : {}
}
```

## Hot Reload Verification

### Frontend Hot Reload
1. Edit any file in `src/` directory
2. Changes should reflect immediately in browser
3. Vite HMR preserves component state when possible

### Backend Hot Reload
1. Edit any file in `backend/` directory
2. uvicorn detects changes and restarts server
3. API endpoints are updated without manual restart

## Networking

### Container Communication
- Frontend container connects to backend via service name `backend-dev:8080`
- Docker network `mai-dev-network` enables cross-container communication
- CORS configured to allow requests from frontend dev server

### Port Mapping
- `localhost:5173` → Frontend (Vite dev server)
- `localhost:8080` → Backend (FastAPI API)

## Volume Mounts

### Frontend Volumes
```yaml
volumes:
  - ./src:/app/src                          # Source code hot reload
  - ./static:/app/static                    # Static assets
  - ./package.json:/app/package.json        # Dependencies
  - ./vite.config.ts:/app/vite.config.ts    # Vite configuration
  - /app/node_modules                       # Preserve dependencies
```

### Backend Volumes
```yaml
volumes:
  - ./backend:/app/backend                  # Backend source code
  - mai-backend-dev-data:/app/backend/data  # Database persistence
  - /app/backend/.venv                      # Virtual environment
```

## Troubleshooting

### Frontend Issues
```bash
# Check frontend container logs
./dev-hot-reload.sh logs-fe

# Rebuild frontend container
./dev-hot-reload.sh build

# Access frontend container
./dev-hot-reload.sh shell-fe
```

### Backend Issues
```bash
# Check backend container logs
./dev-hot-reload.sh logs-be

# Check API health
curl http://localhost:8080/health

# Access backend container
./dev-hot-reload.sh shell-be
```

### Common Problems

1. **Port conflicts**: Ensure ports 5173 and 8080 are available
2. **CORS errors**: Verify `CORS_ALLOW_ORIGIN` includes `http://localhost:5173`
3. **File not updating**: Check volume mounts in `docker-compose.dev.yml`
4. **Container startup fails**: Check `.env.dev` file exists

### Performance Optimization

- Node.js memory limit set to 4GB for complex builds
- Docker layer caching optimized for dependency installation
- Volume mounts exclude `node_modules` to prevent overrides

## Migration from Old System

### Before (Single Container)
```bash
# Required full rebuild for frontend changes
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

### After (Two Container)
```bash
# Simple startup, hot reload handles changes
./dev-hot-reload.sh up
```

## Production Compatibility

- Production builds still use original `Dockerfile`
- Two-container setup is development-only
- Environment variables work seamlessly across both modes
- Database migrations and OpenRouter integration unchanged

## Benefits

1. **Instant Frontend Updates**: Vite HMR provides sub-second update times
2. **Independent Backend Reload**: API changes don't affect frontend state
3. **Better Development Experience**: No more cache busting or full rebuilds
4. **Preserved Application State**: HMR maintains component state when possible
5. **Faster Iteration**: Dramatically reduced development feedback loop

---

**Next Steps**: This hot reload architecture can be extended to support additional development tools like TypeScript watching, linting on save, and automated testing.