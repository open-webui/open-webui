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

### Required Setup
```bash
# Backend (Python 3.11+)
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Docker (Preferred)
python3 generate_client_env_dev.py  # Generate .env.dev
docker-compose -f docker-compose.dev.yml up -d
# Access: http://localhost:3001
```

### Standard Commands
```bash
# Development
./dev.sh                    # Hot reload server
python3 -m pytest tests/    # Run tests

# Docker
docker-compose -f docker-compose.dev.yml logs -f  # View logs
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

### When to Use universal-refactoring-architect
- Files exceeding 700 lines
- Complex architectural changes
- Multi-file refactoring tasks
- Component decomposition

### Usage Pattern
```
Use universal-refactoring-architect agent to [analyze/refactor] {file_path} 
according to {pattern}. Maintain 100% functionality while improving architecture.
```

## Error Prevention

### Common Issues
- **`python: command not found`** → Use `python3`
- **Module import errors** → Activate venv, install requirements
- **PYTHONPATH issues** → Run from `backend/` directory
- **Docker port conflicts** → Check port 3001 availability

### Validation Checklist
```bash
# Before deployment
python3 -m py_compile {modified_files}
curl http://localhost:3001/health
docker-compose -f docker-compose.dev.yml ps  # All services up
```

## Business Context

### Docker Containers
- **`mai-open-webui-dev`**: Development (port 3001)
- **`mai-open-webui-customization`**: Production testing

### Key Integration Points
- **Usage tracking**: Real-time OpenRouter webhooks
- **Multi-tenancy**: Environment-based client isolation
- **Database**: Per-container SQLite with daily aggregation

---

**Core Principle**: Build on OpenWebUI foundation. Preserve existing functionality while enhancing architecture through systematic, safe refactoring.