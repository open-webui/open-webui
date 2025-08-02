# # CLAUDE.md

## Project Context
**mAI** - OpenWebUI fork for Polish SMEs (300+ users)

OpenRouter integration (1.3x markup), SQLite and InfluxDB.

[Important]: Prepare only and exclusively production solutions. It is forbidden by you to manually add, for example, missing tables.

[Important]: Prepare only and exclusively production solutions, especially in the area of initialization processes. It is forbidden by you to manually add, for example, missing tables. Focus on how I will host the future application: Hetzner Cloud and a separate Docker image for each client along with a separate database.

## Critical Development Rules

### Safety-First Approach
- **Work on `develop-b2b` branch only**
- **Preserve business logic 100%** - refactoring moves code, never changes behavior

### Code Quality Standards
- **Max 700 lines per file** - split larger files using systematic refactoring
- **Max 20 lines per function** 
- **Use sub-agents for complex refactoring** tasks
- **Type safety**: 100% TypeScript coverage for new code
- **Follow SOLID principles** for new components

### Python Command Usage
- **ALWAYS use `python3`** - never use `python` command
- **Python executable**: System uses `python3`, not `python`
- **Script execution**: Always run `python3 script_name.py`

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
- **Database**: SQLite, InfluxDB in the future PostresQL [Neon + vectorDB]
- **APIs**: OpenRouter, NBP

### Current Development Environment (Docker Containers)

1. **mai** - Main project container (parent)
2. **backend-dev** (`mai-backend-dev`) - FastAPI backend with hot reload
3. **frontend-dev** (`mai-frontend-dev`) - SvelteKit frontend with Vite HMR
4. **grafana** (`grafana/grafana:latest`) - Monitoring and visualization dashboard
5. **influxdb** (`influxdb:2.7`) - Time-series database for webhook data
6. **nbp-service** (`mai-nbp-service`) - Polish NBP currency exchange rate service

**Development URLs**:
- Frontend: http://localhost:5173 (Vite dev server)
- Backend: http://localhost:8080 (FastAPI with uvicorn --reload)
- InfluxDB UI: http://localhost:8086 (Time-series data visualization)
- Grafana: http://localhost:3000 (Monitoring dashboards)

### Future Stack (InfluxDB Migration)
- **Time-Series DB**: InfluxDB Cloud for webhook data (2-5ms writes)
- **Batch Processing**: Daily at 13:00 CET/CEST
- **NBP Service**: Shared microservice for PLN rates
- **Archive Storage**: Compressed CSV for long-term data

### Key Patterns
- **Extend existing stores** in `/src/lib/stores/` - don't replace
- **Follow router patterns** in `backend/open_webui/routers/usage_tracking.py`
- **Use existing models**: `ClientOrganization`, `ClientDailyUsage`, `ClientUserDailyUsage`

## ## 🎯 SUB-AGENT USAGE GUIDELINES

### When to Use code-quality-architect
- Files exceeding 700 lines requiring refactoring
- Complex architectural changes
- Multi-file refactoring tasks
- Component decomposition
- Code quality improvements and bug detection
- Docker and development environment issues
- Container orchestration problems
- Hot reload and build system fixes

### When to Use business-logic-analyst
- Documenting function workflows and business processes
- Creating workflow reports for complex features
- Mapping business logic flow from input to output
- Understanding how features work end-to-end

### When to Use debugging-specialist
- Investigating bugs and functional issues
- Root cause analysis of application problems
- Systematic bug isolation and resolution
- API failures and data inconsistencies

### When to Use repository-analyzer
- Comprehensive codebase assessment
- Performance bottleneck identification
- Strategic refactoring planning
- Technical debt analysis and prioritization

### Usage Patterns
```bash
# For code refactoring and quality issues
Use code-quality-architect agent to [analyze/refactor] {file_path} 
according to {pattern}. Maintain 100% functionality.

# For development environment issues
Use code-quality-architect agent to [analyze/fix] development environment

# For workflow documentation
Use business-logic-analyst agent to analyze and document the {feature_name} 
workflow. Generate report in docs/{feature}-workflow-analysis.md

# For bug investigation
Use debugging-specialist agent to investigate {issue_description} 
and identify root cause with systematic analysis.

# For repository analysis
Use repository-analyzer agent to perform comprehensive analysis 
and generate refactoring recommendations prioritized by functionality.


## Business Context

### Key Integration Points
- **Usage tracking**

## InfluxDB Migration Plan

### Development Environment Setup
1. **Local InfluxDB**: Docker Compose with dev configuration
2. **Feature Flags**: `INFLUXDB_ENABLED` environment variable
3. **Dual-Write Mode**: Write to both SQLite and InfluxDB for validation
4. **NBP Service**: Standalone microservice with mock mode

**Development Commands**:
```bash
*# Start development environment*
docker-compose -f docker-compose.dev.yml up

*# Start individual services*
docker-compose -f docker-compose.dev.yml up backend-dev
docker-compose -f docker-compose.dev.yml up frontend-dev
docker-compose -f docker-compose.dev.yml up influxdb

*# View logs*
docker-compose -f docker-compose.dev.yml logs -f backend-dev
docker-compose -f docker-compose.dev.yml logs -f influxdb

*# Stop environment*
docker-compose -f docker-compose.dev.yml down
```

**Container Networking**:
- Backend communicates with InfluxDB via `http://mai-influxdb-dev:8086`
- NBP service accessible at `http://mai-nbp-service:8001`
- All containers connected via `mai-dev-network`


**Core Principle**: Build on OpenWebUI foundation. Preserve existing functionality while enhancing architecture through systematic, safe refactoring.

**For InfluxDB migration details, see: `new_deployment.md`**
