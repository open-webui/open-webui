# CLAUDE.md

## Core Project Rules

**mAI** - OpenWebUI fork for Polish SMEs (300+ users, 20 Docker instances)

### Critical Rules (Non-Negotiable)
- **NEVER exceed 700 lines per file** - split into smaller modules
- **ALWAYS work on `customization` branch** - never commit to `main`
- **ALWAYS backup assets**: `cp -r static/static customization-backup/static-$(date +%Y%m%d)`
- **Production solutions only** - no manual fixes or temporary hacks
- **Sequential Thinking MCP** for complex problems

### Commit Prefixes (Mandatory)
```
brand:    # mAI branding changes
theme:    # UI styling modifications  
ui:       # Interface improvements
assets:   # Static file changes
feat:     # New features
fix:      # Bug fixes
refactor: # Code improvements
```

### Code Quality Standards
- **Max function length**: 20 lines
- **Type safety**: 100% TypeScript coverage for new code
- **Error handling**: Structured exceptions with proper HTTP codes
- **SOLID principles**: Apply to new components only

### Business Context
- **Multi-tenant**: Docker isolation per client via environment variables
- **Usage tracking**: Real-time OpenRouter integration with 1.3x markup
- **Database**: SQLite per container, daily usage aggregation
- **Deployment**: Single Hetzner server, docker-compose per client

### Docker Development Environment
- **`mai-open-webui-dev`**: Development container running on port 3001
  - Used for testing new features and debugging
  - Environment-based configuration with `OPENROUTER_EXTERNAL_USER=dev_mai_client_d460a478`
  - Hot reload for rapid development
- **`mai-open-webui-customization`**: Production-ready container for customization branch
  - Used for testing production deployments and client customizations
  - Full production environment simulation
  - Stable build for client testing

## Key Implementation Notes

- **Database**: Use existing models in `backend/open_webui/models/organization_usage.py`
- **Frontend**: Extend stores in `/src/lib/stores/index.ts`, don't replace
- **Routers**: Follow patterns in `backend/open_webui/routers/usage_tracking.py`
- **Environment**: Use `generate_client_env.py` for client setup

## Architecture Context

### Current Tech Stack
```
Frontend: SvelteKit + TypeScript + TailwindCSS
Backend: FastAPI + SQLAlchemy + Redis
Database: SQLite (per container)
APIs: OpenRouter with usage webhooks
```

### Key Existing Models (Don't Modify)
- `ClientOrganization` - Client management with API keys
- `ClientDailyUsage` - Daily usage aggregation 
- `ClientUserDailyUsage` - Per-user tracking
- `ProcessedGeneration` - Duplicate prevention

### Extend, Don't Replace
- Use existing `Users` model from OpenWebUI
- Extend existing stores in `/src/lib/stores/`
- Add routers following existing patterns
- Follow existing auth and permission patterns

## Development Environment Setup

### Python Environment (Required Before Any Development)
```bash
# Navigate to project root
cd /path/to/mAI

# Check Python availability
python3 --version  # Required: 3.11+ (project requirement)

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import typer; print('Dependencies OK')"
```

### Standard Commands (Always Use These)
```bash
# Testing (from backend/ directory with venv activated)
cd backend && source venv/bin/activate
python3 -m pytest tests/
python3 backend/tests/test_dynamic_pricing.py  # Direct script execution

# Development server
cd backend && source venv/bin/activate
./dev.sh  # Hot reload development server

# Production server  
cd backend && source venv/bin/activate
./start.sh
```

### Docker Development (Preferred)
```bash
# First time setup
python3 generate_client_env_dev.py  # Generate .env.dev
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
# Access: http://localhost:3001

# Daily development
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f
```

### Environment Validation Before Tests
```bash
# Run this before any Python testing
cd backend
source venv/bin/activate
python3 -c "
import sys
sys.path.insert(0, '.')
from open_webui.utils.openrouter_models import get_dynamic_model_pricing
print('✅ Environment ready')
"
```

### Common Error Solutions
- **`python: command not found`** → Use `python3`
- **`ModuleNotFoundError: No module named 'typer'`** → Activate venv, install requirements
- **Import errors in tests** → Run from `backend/` directory with activated venv
- **`PYTHONPATH` issues** → Use `python3 -m pytest` instead of direct script execution

## MCP Research Process
1. **Code patterns**: `search_code_examples` for existing implementations
2. **Documentation**: `perform_rag_query` with source filtering  
3. **Complex problems**: Sequential Thinking MCP
4. **Integration**: Check existing OpenWebUI patterns first

---

**Core Principle**: Build on the solid OpenWebUI foundation. Usage tracking and multi-tenancy are operational - focus on enhancing existing functionality.