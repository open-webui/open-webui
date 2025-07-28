# CLAUDE.md

## Project Context
**mAI** - OpenWebUI fork for Polish SMEs (300+ users, 20 Docker instances)

Multi-tenant SaaS with Docker isolation, OpenRouter integration (1.3x markup), SQLite per container.

## Critical Development Rules

### Safety-First Approach
- **ALWAYS backup before changes**: `git add . && git commit -m "CHECKPOINT: {description}"`
- **Work on `customization` branch only** - never commit to `main`
- **Test after every change**: Verify imports and basic functionality work
- **Preserve business logic 100%** - refactoring moves code, never changes behavior

### Code Quality Standards
- **Max 700 lines per file** - split larger files using systematic refactoring
- **Max 20 lines per function** 
- **Use sub-agents for complex refactoring** tasks
- **Type safety**: 100% TypeScript coverage for new code
- **Follow SOLID principles** for new components

### Commit Conventions
```
feat:     # New features
fix:      # Bug fixes  
refactor: # Code improvements
ui:       # Interface changes
brand:    # mAI branding
theme:    # Styling
assets:   # Static files
```

## Development Environment

### Hot Reload Development (Recommended)
```bash
# Two-Container Architecture with Full Hot Reload
python3 generate_client_env_dev.py  # Generate .env.dev (if needed)
./dev-hot-reload.sh up              # Start both containers

# 🚀 Primary Development URL: http://localhost:5173
# Backend API endpoint:       http://localhost:8080
# Health check:               http://localhost:8080/health
```

### Development Architecture
- **Frontend Container** (`mai-frontend-dev`): Vite dev server with Hot Module Replacement (HMR)
- **Backend Container** (`mai-backend-dev`): FastAPI with uvicorn --reload  
- **Independent Hot Reload**: Frontend and backend reload separately without interference
- **Cross-Container Communication**: Docker networking with API proxy
- **Instant Updates**: Sub-second frontend changes via HMR, automatic backend restart

### Daily Development Workflow
```bash
# 1. Start Development Environment
./dev-hot-reload.sh up      # Start both containers with hot reload

# 2. Develop with Instant Updates
# - Edit .svelte, .ts, .css files → Frontend updates instantly via HMR
# - Edit .py files in backend/ → Backend restarts automatically  
# - Access: http://localhost:5173 (main development URL)

# 3. Stop When Done
./dev-hot-reload.sh down    # Stop all containers
```

### Management Commands
```bash
# Container Management
./dev-hot-reload.sh status    # Check container status
./dev-hot-reload.sh restart   # Restart both containers
./dev-hot-reload.sh clean     # Clean up containers

# Debugging & Logs  
./dev-hot-reload.sh logs-fe   # Frontend logs
./dev-hot-reload.sh logs-be   # Backend logs
./dev-hot-reload.sh shell-fe  # Access frontend container
./dev-hot-reload.sh shell-be  # Access backend container
./dev-hot-reload.sh help      # Show all available commands

# Testing
python3 -m pytest tests/     # Run tests (from host or backend container)
```

### Alternative Development Methods
```bash
# Legacy Single Container (Backup - requires rebuilds for UI changes)
docker-compose -f docker-compose.dev.yml up -d  # Port 3001

# Local Development (No Docker)
cd backend && ./dev.sh     # Backend only (port 8080)
npm run dev               # Frontend only (port 5173)
```

## Architecture Guidelines

### Current Stack
- **Frontend**: SvelteKit + TypeScript + TailwindCSS
- **Backend**: FastAPI + SQLAlchemy + Redis  
- **Database**: SQLite per container
- **APIs**: OpenRouter with usage webhooks

### Key Patterns
- **Extend existing stores** in `/src/lib/stores/` - don't replace
- **Follow router patterns** in `backend/open_webui/routers/usage_tracking.py`
- **Use existing models**: `ClientOrganization`, `ClientDailyUsage`, `ClientUserDailyUsage`
- **Environment setup**: Use `generate_client_env.py` for client configuration

## Sub-Agent Usage

### When to Use code-quality-architect
- Docker and development environment issues
- Container orchestration problems
- Hot reload and build system fixes
- Development workflow optimization

### When to Use universal-refactoring-architect
- Files exceeding 700 lines
- Complex architectural changes
- Multi-file refactoring tasks
- Component decomposition

### Usage Patterns
```bash
# For development environment issues
Use code-quality-architect agent to [analyze/fix] development environment
focusing on [hot reload/Docker/build system]. Ensure reliable workflow.

# For code refactoring
Use universal-refactoring-architect agent to [analyze/refactor] {file_path} 
according to {pattern}. Maintain 100% functionality while improving architecture.
```

## Error Prevention

### Common Issues

**Hot Reload Environment:**
- **Port conflicts** → Check ports 5173 (frontend) and 8080 (backend) availability
- **Hot reload not working** → Verify containers have proper volume mounts with `./dev-hot-reload.sh status`
- **API calls failing** → Check Docker network connectivity: `./dev-hot-reload.sh logs-be`
- **Frontend not updating** → Ensure HMR is working, check browser console for WebSocket connection
- **Backend not restarting** → Check volume mount for `backend/` directory in container

**General Issues:**
- **`python: command not found`** → Use `python3`
- **Module import errors** → Activate venv, install requirements
- **PYTHONPATH issues** → Run from `backend/` directory

### Development Validation Checklist
```bash
# Hot Reload Environment Health Check
./dev-hot-reload.sh status              # Check both containers running
./dev-hot-reload.sh logs-fe | head       # Frontend startup logs (Vite ready)
./dev-hot-reload.sh logs-be | head       # Backend startup logs (uvicorn ready)

# Test Hot Reload Functionality
# 1. Edit a .svelte file → Check browser updates instantly
# 2. Edit a .py file in backend/ → Check backend restarts in logs
# 3. Make API call from frontend → Verify cross-container communication

# Manual Health Verification (if needed)
curl http://localhost:5173              # Frontend responds
curl http://localhost:8080/health       # Backend health endpoint

# Legacy Single Container (Backup)
curl http://localhost:3001/health
docker-compose -f docker-compose.dev.yml ps

# Before Deployment
python3 -m py_compile {modified_files}  # Syntax check
```

## Business Context

### Docker Containers

**Hot Reload Development (Primary):**
- **`mai-frontend-dev`**: Vite dev server (port 5173) with HMR
- **`mai-backend-dev`**: FastAPI with hot reload (port 8080)

**Legacy Single Container (Backup):**
- **`mai-open-webui-dev`**: Combined container (port 3001)
- **`mai-open-webui-customization`**: Production testing

### Key Integration Points
- **Usage tracking**: Real-time OpenRouter webhooks
- **Multi-tenancy**: Environment-based client isolation
- **Database**: Per-container SQLite with daily aggregation

---

## Hot Reload Benefits Achieved

### Key Improvements vs. Legacy Setup
- **Instant Frontend Updates**: Sub-second changes via Vite HMR (vs. full Docker rebuilds)
- **Component State Preservation**: HMR maintains UI state when possible
- **Independent Hot Reload**: Frontend and backend reload separately without interference  
- **No Cache Busting**: Eliminated need for `docker build --no-cache`
- **Development Speed**: ~10x faster iteration cycle for UI changes
- **Production Compatibility**: Original Dockerfile and build process unchanged

### Architecture Benefits
- **Separation of Concerns**: Frontend and backend containers have distinct responsibilities
- **Scalable Development**: Easy to add more developers without build conflicts
- **Container Specialization**: Each container optimized for its specific purpose
- **Docker Best Practices**: Proper networking, health checks, and volume management

---

**Core Principle**: Build on OpenWebUI foundation. Preserve existing functionality while enhancing architecture through systematic, safe refactoring.