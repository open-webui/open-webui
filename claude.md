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

## Sub-Agent Usage

### When to Use code-quality-architect
- Docker and development environment issues
- Container orchestration problems
- Hot reload and build system fixes

### When to Use universal-refactoring-architect
- Files exceeding 700 lines
- Complex architectural changes
- Multi-file refactoring tasks

### Usage Patterns
```bash
# For development environment issues
Use code-quality-architect agent to [analyze/fix] development environment

# For code refactoring
Use universal-refactoring-architect agent to [analyze/refactor] {file_path} 
according to {pattern}. Maintain 100% functionality.
```

## Business Context

### Key Integration Points
- **Usage tracking**: Real-time OpenRouter webhooks
- **Multi-tenancy**: Environment-based client isolation
- **Database**: Per-container SQLite with daily aggregation

---

**Core Principle**: Build on OpenWebUI foundation. Preserve existing functionality while enhancing architecture through systematic, safe refactoring.

**For detailed development setup and commands, see: `DEV_ENVIRONMENT_GUIDE.md`**