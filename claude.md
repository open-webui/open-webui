# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is mAI, a customized fork of Open WebUI - a feature-rich, extensible AI platform that operates entirely offline. The project supports various LLM runners like Ollama and OpenAI-compatible APIs, with built-in inference engine for RAG (Retrieval Augmented Generation).

**Current Version:** 0.6.17 (upgraded from Open WebUI on January 19, 2025)

**Key customizations:**
- Renamed from "Open WebUI" to "mAI" 
- Added tagline "You + AI = superpowers! 🚀" (with Polish localization: "Ty + AI = supermoce! 🚀")
- Custom branding and logo replacement capabilities
- Custom background patterns feature with opacity controls
- Complete favicon and PWA manifest implementation
- Currently on branch: `customization` (main branch: `main`)

**Recent Updates:**
- Successfully merged Open WebUI v0.6.17 preserving all customizations
- Upgraded to Tiptap v3 for rich text editing
- Installed FFmpeg for full audio processing support
- Complete mAI visual identity system implemented (January 20, 2025)
- Documentation reorganized into structured categories (January 20, 2025)
- Fixed favicon display issues in production (January 21, 2025)
- See `docs/development/upgrade-guide.md` for detailed upgrade process documentation

## Architecture

### Frontend (SvelteKit)
- **Framework**: SvelteKit with TypeScript
- **Styling**: TailwindCSS with custom themes
- **Build Tool**: Vite
- **Key Dependencies**: 
  - Rich text editing with TipTap
  - Chart.js for data visualization
  - Pyodide for Python code execution
  - Socket.io for real-time communication
  - Extensive i18n support (20+ languages)

### Backend (FastAPI)
- **Framework**: FastAPI with Python 3.11-3.12
- **Database**: SQLAlchemy with Alembic migrations, supports PostgreSQL, MySQL, SQLite
- **Vector DBs**: ChromaDB, Qdrant, Milvus, Pinecone, OpenSearch, ElasticSearch
- **Authentication**: JWT with OAuth support
- **AI Integration**: OpenAI, Anthropic, Google Gemini APIs
- **Document Processing**: Unstructured, PyPDF, python-pptx, docx2txt
- **Audio**: Faster-whisper for transcription
- **Web Search**: Multiple providers (SearXNG, Brave, DuckDuckGo, etc.)

## Development Commands

### Start Development Environment
```bash
# Start both frontend and backend servers (recommended)
./start-dev.sh

# OR manually:
# Terminal 1: Backend
cd backend
source .venv/bin/activate
sh dev.sh  # Starts uvicorn on port 8080

# Terminal 2: Frontend
npm run dev        # Starts Vite dev server on port 5173
npm run dev:5050   # Alternative: Start on port 5050
```

### Development Testing Policy
**IMPORTANT: DO NOT test solutions by running the development server.** The user always has the server and mAI application running in a new tab and sees changes in real time or reloads the server manually. Focus on code verification through build processes and type checking instead.

### Build and Testing
```bash
# Frontend
npm run build              # Build for production (includes pyodide fetch)
npm run build:watch        # Build for production with watch mode
npm run preview            # Preview production build
npm run check              # Type checking with svelte-check
npm run check:watch        # Type checking with watch mode
npm run test:frontend      # Run Vitest tests

# Linting and Formatting
npm run lint               # Lint frontend, types, and backend
npm run lint:frontend      # ESLint for frontend with auto-fix
npm run lint:types         # Type checking (alias for check)
npm run lint:backend       # Pylint for backend
npm run format             # Prettier for frontend
npm run format:backend     # Black for backend

# Internationalization
npm run i18n:parse         # Parse i18n files and format them

# Backend Development
cd backend
black .                    # Format Python code
```

### Database Operations
```bash
cd backend
# Database migrations are handled by Alembic
python -m alembic upgrade head  # Apply migrations
python -m alembic revision --autogenerate -m "description"  # Create migration
```

### Docker Operations

#### Development with Docker (Recommended)
```bash
# Use host Ollama (recommended for local development)
docker compose -f docker-compose-host-ollama.yaml up -d

# Or use Docker Ollama (creates isolated instance)
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

#### Production Deployment
```bash
# Via Makefile
make install              # docker-compose up -d
make start               # docker-compose start
make stop                # docker-compose stop
make update              # Pull, rebuild, restart
```

## Docker Configuration Best Practices

### Local Development Setup
Use `docker-compose-host-ollama.yaml` to connect to your host Ollama installation:
```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    volumes:
      - open-webui:/app/backend/data
    environment:
      - 'OLLAMA_BASE_URL=http://host.docker.internal:11434'
      - 'WEBUI_NAME=mAI'
    ports:
      - 3000:8080
    extra_hosts:
      - host.docker.internal:host-gateway

volumes:
  open-webui:
    external: true
    name: mai_open-webui  # Use existing volume with data
```

### Important Docker Notes
- **Always use named volumes** with `external: true` to preserve data
- **Never create new volumes** unless intentionally starting fresh
- **For updates**: Copy files directly to running container instead of rebuilding
- **Browser caching**: Always clear cache after favicon/asset updates

### Quick Updates Without Rebuilding
```bash
# Copy updated files directly to running container
docker cp static/static/favicon.ico open-webui:/app/backend/static/
docker cp static/static/favicon.png open-webui:/app/backend/static/
docker cp static/manifest.json open-webui:/app/backend/static/
docker restart open-webui
```

## Key File Locations

### Configuration
- `backend/open_webui/config.py` - Main backend configuration
- `backend/open_webui/constants.py` - Application constants
- `src/lib/constants.ts` - Frontend constants
- `svelte.config.js` - SvelteKit configuration
- `vite.config.ts` - Vite build configuration

### API Structure
- `backend/open_webui/routers/` - FastAPI route handlers
- `backend/open_webui/models/` - SQLAlchemy ORM models
- `backend/open_webui/utils/` - Utility functions
- `src/lib/apis/` - Frontend API client functions

### Frontend Components
- `src/lib/components/` - Reusable Svelte components
- `src/routes/` - SvelteKit pages and layouts
- `src/lib/stores/` - Svelte stores for state management
- `src/lib/i18n/` - Internationalization files

### Customization Assets
- `static/static/` - Frontend favicon and logo assets (complete mAI visual identity)
- `backend/open_webui/static/` - Backend static assets (complete mAI visual identity)  
- `mai_logos/` - Source files for all mAI graphic assets (11 files)
- `static/custom.css` - Custom CSS overrides
- `static/manifest.json` - PWA manifest with mAI branding

## Architecture Patterns

### Backend Patterns
- **Dependency Injection**: FastAPI's dependency system for database sessions, auth
- **Repository Pattern**: Models in `backend/open_webui/models/` with separate business logic
- **Router Organization**: Feature-based routing in `routers/` directory
- **Middleware Chain**: Authentication, CORS, compression middleware
- **Database Abstraction**: SQLAlchemy ORM with Alembic migrations

### Frontend Patterns
- **Component Architecture**: Feature-based component organization
- **Store Pattern**: Svelte stores for global state management
- **API Client Pattern**: Centralized API functions in `src/lib/apis/`
- **Layout Hierarchy**: Nested layouts in SvelteKit route structure
- **Reactive Programming**: Svelte's reactive declarations and stores

### Data Flow
1. **Authentication**: JWT tokens with refresh mechanism
2. **Real-time Updates**: Socket.io for live chat and notifications
3. **File Upload**: Chunked uploads with progress tracking
4. **RAG Pipeline**: Document ingestion → Vector embedding → Retrieval → Generation
5. **Multi-model Support**: Abstracted model interface supporting various LLM providers

## Testing Strategy

### Frontend Testing
- **Unit Tests**: Vitest for component and utility testing
- **E2E Tests**: Cypress for user flow testing (use `npm run cy:open`)
- **Type Safety**: TypeScript with strict mode

### Backend Testing
- **Code Quality**: Black for formatting, Pylint for linting
- **Type Safety**: Python type hints with modern syntax
- **Manual Testing**: Use dev.sh for development server testing

## Development Workflow

### Branch Strategy
- `main` - Production-ready code
- `customization` - Current working branch for mAI customizations
- Feature branches for specific improvements

### Code Quality
- **Frontend**: ESLint + Prettier + TypeScript
- **Backend**: Black + Pylint + mypy (type checking)
- **Pre-commit**: Automated formatting and linting

### Custom Branding & Customization
- **Logo Assets**: Located in `static/static/` and `backend/open_webui/static/`
- **Custom CSS**: `static/custom.css` for theme overrides
- **Themes**: `static/themes/` for custom theme definitions
- **Branding Rules**: See `.cursor/rules/project.mdc` for detailed customization guidelines
- **License Compliance**: White-labeling allowed for ≤50 users with attribution requirements

### Customization Workflow
- **ALWAYS** work on `customization` branch (never commit to main)
- **ALWAYS** create backups before modifications: `cp -r static/static customization-backup/static-$(date +%Y%m%d)`
- **Required Testing**: All theme variants (Light/Dark/OLED/"Her"), mobile responsiveness
- **Asset Requirements**: Logo files <100KB, proper format requirements (PNG for logos, ICO for favicons, SVG for scalable)
- **Commit Prefixes**: `brand:`, `theme:`, `ui:`, `assets:` for organized changes
- **Quality Standards**: WCAG 2.1 AA compliance, contrast ratios 4.5:1 minimum

### Documentation Organization
- **Main Documentation**: Located in `docs/` directory with subdirectories for different categories
- **Deployment Guides**: `docs/deployment/` - Production deployment instructions
- **Development Docs**: `docs/development/` - Contributing, upgrading, and development scripts
- **Customization Docs**: `docs/customization/` - mAI-specific changes and plans
- **Operations Docs**: `docs/operations/` - Installation, troubleshooting, security
- **Configuration Docs**: `docs/configuration/` - Server and proxy configurations
- **Documentation Index**: `docs/README.md` - Central hub for all documentation

### Deployment
- **Docker**: Multi-stage builds for production
- **Static Assets**: Vite builds to `build/` directory
- **Database**: Automatic migrations on container start
- **Volume Management**: Use named volumes with `external: true` for data persistence

## Performance Considerations

### Frontend Optimization
- **Code Splitting**: Dynamic imports for route-based splitting
- **Asset Optimization**: Vite's built-in optimization
- **Service Worker**: PWA capabilities for offline access
- **Lazy Loading**: Virtual scrolling for large lists

### Backend Optimization
- **Database Indexing**: Proper indexes on frequently queried fields
- **Connection Pooling**: SQLAlchemy connection management
- **Caching**: Redis integration for session and data caching
- **Async Operations**: FastAPI's async capabilities for I/O operations

## Security Features

- **Authentication**: JWT with configurable expiration
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Pydantic models for request validation
- **CORS**: Configurable cross-origin resource sharing
- **Rate Limiting**: Built-in API rate limiting
- **File Upload Security**: Type validation and size limits

## LLM Integration Architecture

### Model Abstraction
- **Unified Interface**: Common API for different LLM providers
- **Provider Support**: OpenAI, Anthropic, Google, Ollama, custom APIs
- **Model Management**: Dynamic model loading and configuration
- **Streaming Support**: Real-time response streaming

### RAG Implementation
- **Document Processing**: Multi-format document ingestion
- **Vector Storage**: Multiple vector database backends
- **Retrieval Strategies**: Various search and ranking algorithms
- **Context Management**: Intelligent context window management

## Customization Framework

### Theme System
- **CSS Variables**: Theme-based styling system
- **Asset Replacement**: Logo and favicon customization
- **Brand Colors**: Configurable color schemes
- **Layout Customization**: Flexible UI component arrangement

### Internationalization
- **i18next**: Full i18n support with 20+ languages
- **Dynamic Loading**: Lazy-loaded translation files
- **RTL Support**: Right-to-left language support
- **Pluralization**: Advanced plural form handling

## Environment Variables

### Key Environment Variables
- `PORT` - Backend server port (default: 8080)
- `OLLAMA_BASE_URL` - Ollama server URL
- `OPENAI_API_KEY` - OpenAI API key
- `HF_HUB_OFFLINE` - Set to `1` for offline mode
- `ENV` - Environment (dev/prod)
- `WEBUI_NAME` - Application name (default: mAI)
- `WEBUI_URL` - Application URL

### Setting Environment Variables
```bash
# Development
export PORT=8080
export OLLAMA_BASE_URL=http://localhost:11434

# Production
export ENV=prod
```

## Error Handling Patterns

### Backend Error Handling
- **Follow-up Generation**: Wrapped in try-catch to prevent Ollama failures from crashing chat sessions
- **Background Tasks**: Protected with error handling to ensure main chat flow continues even if background operations fail
- **Model Runner Failures**: Gracefully handled to prevent "model runner has unexpectedly stopped" errors from affecting user experience

### Frontend Error Handling
- **API Calls**: All API functions in `src/lib/apis/` include error handling
- **Socket.io Reconnection**: Automatic reconnection logic for real-time features
- **Form Validation**: Client-side validation before API submission

## Common Workflows

### Adding New Language Support
1. Add language to `src/lib/i18n/locales/languages.json`
2. Create translation file: `src/lib/i18n/locales/[lang-CODE]/translation.json`
3. Run `npm run i18n:parse` to format
4. Test with UI language switcher

### Modifying Chat Interface
1. Main placeholder: `src/lib/components/chat/Placeholder.svelte`
2. Message components: `src/lib/components/chat/Messages/`
3. Input handling: `src/lib/components/chat/MessageInput.svelte`
4. Chat settings: `src/lib/components/chat/Settings/`

### Backend API Development
1. Create router in `backend/open_webui/routers/`
2. Add models in `backend/open_webui/models/`
3. Register router in `backend/open_webui/main.py`
4. Create frontend API client in `src/lib/apis/`

## Debug and Monitoring

### Backend Logging
- Log configuration in `backend/open_webui/utils/misc.py`
- Use `log.info()`, `log.error()` with proper context
- Exception logging with `exc_info=True` for stack traces

### Frontend Debugging
- Browser DevTools for network and console debugging
- Svelte DevTools for component inspection
- `$inspect()` for reactive debugging in Svelte 5

### Performance Monitoring
- Backend: FastAPI middleware timing
- Frontend: Vite build analysis with `npm run build -- --sourcemap`
- Database: Query performance with SQLAlchemy logging

## Upgrading from Open WebUI

### Process Overview
When upgrading mAI to incorporate new Open WebUI releases:

1. **Preparation**
   - Ensure clean working directory
   - Create backup branch
   - Verify upstream remote is configured

2. **Merge Process**
   - Fetch and merge specific version tag
   - Resolve conflicts preserving mAI customizations
   - Special attention to: package.json, Chat.svelte, Polish translations

3. **Post-Merge**
   - Update dependencies with `npm install --force`
   - Build and test thoroughly
   - Revert workflow files if lacking GitHub permissions

4. **Documentation**
   - See `docs/development/upgrade-guide.md` for detailed step-by-step instructions
   - Document any new conflicts or issues for future upgrades

### Critical Files to Preserve During Upgrades
- `package.json`: Keep "name": "mai"
- `src/lib/components/chat/Chat.svelte`: Background pattern functionality
- `src/lib/components/chat/Placeholder.svelte`: Custom branding
- `src/lib/i18n/locales/pl-PL/translation.json`: Polish customizations
- Theme and asset files in `static/`
- `static/manifest.json`: PWA manifest with mAI branding
- `src/app.html`: Favicon references

## Docker Volume Management

### Best Practices
1. **Named Volumes**: Always use explicitly named volumes
2. **External Volumes**: Use `external: true` to reference existing volumes
3. **Data Persistence**: Never delete volumes without backup
4. **Volume Inspection**: Use `docker volume ls` and `docker volume inspect`

### Common Issues
- **Multiple volumes with same data**: Check timestamps to identify the active one
- **Lost data after rebuild**: Always use `external: true` for existing volumes
- **Ollama models missing**: Connect to host Ollama or mount host directory

### Cleanup Commands
```bash
# List volumes
docker volume ls | grep mai

# Remove unused volumes (careful!)
docker volume prune

# Inspect volume contents
docker run --rm -v volume_name:/data alpine ls -la /data/
```