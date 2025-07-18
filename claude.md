# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is mAI, a customized fork of Open WebUI - a feature-rich, extensible AI platform that operates entirely offline. The project supports various LLM runners like Ollama and OpenAI-compatible APIs, with built-in inference engine for RAG (Retrieval Augmented Generation).

**Key customizations:**
- Renamed from "Open WebUI" to "mAI" 
- Added tagline "You + AI = superpowers! 🚀"
- Custom branding and logo replacement capabilities
- Currently on branch: `customization` (main branch: `main`)

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
# Start both frontend and backend servers
./start-dev.sh

# OR manually:
# Terminal 1: Backend
cd backend
source .venv/bin/activate
sh dev.sh  # Starts uvicorn on port 8080

# Terminal 2: Frontend
npm run dev  # Starts Vite dev server on port 5173
```

### Build and Testing
```bash
# Frontend
npm run build              # Build for production
npm run preview           # Preview production build
npm run check             # Type checking with svelte-check
npm run test:frontend     # Run Vitest tests

# Linting and Formatting
npm run lint              # Lint frontend, types, and backend
npm run lint:frontend     # ESLint for frontend
npm run lint:backend      # Pylint for backend
npm run format            # Prettier for frontend
npm run format:backend    # Black for backend

# Backend Testing
cd backend
pytest                    # Run backend tests
black .                   # Format Python code
```

### Database Operations
```bash
cd backend
# Database migrations are handled by Alembic
python -m alembic upgrade head  # Apply migrations
python -m alembic revision --autogenerate -m "description"  # Create migration
```

### Docker Operations
```bash
# Via Makefile
make install              # docker-compose up -d
make start               # docker-compose start
make stop                # docker-compose stop
make update              # Pull, rebuild, restart
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
- `static/static/` - Frontend favicon and logo assets
- `backend/open_webui/static/` - Backend static assets
- `static/custom.css` - Custom CSS overrides

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
- **E2E Tests**: Cypress for user flow testing
- **Type Safety**: TypeScript with strict mode

### Backend Testing
- **Unit Tests**: pytest for individual function testing
- **Integration Tests**: Database and API endpoint testing
- **Docker Testing**: pytest-docker for containerized testing

## Development Workflow

### Branch Strategy
- `main` - Production-ready code
- `customization` - Current working branch for mAI customizations
- Feature branches for specific improvements

### Code Quality
- **Frontend**: ESLint + Prettier + TypeScript
- **Backend**: Black + Pylint + mypy (type checking)
- **Pre-commit**: Automated formatting and linting

### Deployment
- **Docker**: Multi-stage builds for production
- **Static Assets**: Vite builds to `build/` directory
- **Database**: Automatic migrations on container start

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