# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open WebUI is a feature-rich, self-hosted AI platform that operates entirely offline. It's built as a full-stack web application supporting various LLM runners like Ollama and OpenAI-compatible APIs, with built-in RAG capabilities. The project uses:
- **Backend**: Python (FastAPI) with SQLAlchemy for database management
- **Frontend**: SvelteKit with static adapter
- **Real-time**: Socket.IO for WebSocket support
- **Database**: SQLAlchemy with Alembic migrations (supports PostgreSQL, MySQL, SQLite)
- **Deployment**: Docker-first with Kubernetes support

## Development Commands

### Frontend Development
```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Build frontend for production
npm run build

# Preview production build
npm run preview

# Lint frontend code
npm run lint:frontend

# Format frontend code
npm run format

# Type checking
npm run check
```

### Backend Development
```bash
# Start backend dev server (with auto-reload)
cd backend
./dev.sh
# Or manually:
PORT=8080 uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --forwarded-allow-ips '*' --reload

# Format Python code
npm run format:backend
# Or directly:
black . --exclude ".venv/|/venv/"

# Lint Python code
npm run lint:backend
# Or directly:
cd backend && pylint open_webui/
```

### Testing
```bash
# Run frontend tests
npm run test:frontend

# Run backend tests (pytest)
cd backend
pytest backend/open_webui/test/

# Run specific test file
pytest backend/open_webui/test/apps/webui/routers/test_chats.py

# Run with verbose output
pytest -v backend/open_webui/test/
```

### Database Migrations
```bash
# Migrations run automatically on startup via config.py:run_migrations()
# To create a new migration (from backend directory):
cd backend
alembic revision -m "description of changes"

# Migrations are located in: backend/open_webui/migrations/versions/
```

### Docker Commands
```bash
# Using Makefile
make install        # Start with docker-compose
make start         # Start containers
make stop          # Stop containers
make update        # Pull, rebuild, and restart

# Or directly with docker-compose
docker-compose up -d
docker-compose up -d --build
```

## Architecture Overview

### Backend Structure (`backend/open_webui/`)

**Core Application Files:**
- `main.py` - FastAPI application entry point with all route registrations, middleware setup, and lifespan management
- `config.py` - Configuration management with database-backed settings and migration runner
- `env.py` - Environment variable parsing and validation
- `constants.py` - Application-wide constants
- `tasks.py` - Background task definitions (APScheduler)

**Database Layer:**
- `internal/db.py` - SQLAlchemy Base and session management
- `models/` - SQLAlchemy ORM models (users, chats, messages, files, etc.)
  - Each model file contains both the SQLAlchemy model (e.g., `Chat(Base)`) and a corresponding Table class (e.g., `ChatTable`) with CRUD operations
  - Important models: `users.py`, `chats.py`, `messages.py`, `token_usage.py`, `groups.py`
- `migrations/versions/` - Alembic migration files for schema changes

**API Routers (`routers/`):**
- `auths.py` - Authentication, signup, signin, OAuth
- `chats.py` - Chat CRUD operations
- `openai.py` - OpenAI-compatible API endpoints (main LLM interface)
- `ollama.py` - Ollama-specific API endpoints
- `retrieval.py` - RAG (Retrieval Augmented Generation) endpoints
- `files.py` - File upload and management
- `users.py` - User management
- `models.py` - Model management
- `tools.py`, `functions.py` - Custom tools and function calling
- `pipelines.py` - Pipeline plugin integration
- `audio.py`, `images.py` - Media generation endpoints

**RAG/Retrieval System (`retrieval/`):**
- `loaders/` - Document loaders for various file types
- `vector/` - Vector database integrations (ChromaDB, Milvus, Qdrant, etc.)
- `web/` - Web scraping and search integrations
- `utils.py` - RAG utilities and embedding functions

**Real-time Layer (`socket/`):**
- `main.py` - Socket.IO server for WebSocket connections, user presence, collaborative editing (CRDT with Yjs), and token usage tracking
- `utils.py` - Redis-based utilities for distributed state (RedisDict, RedisLock, YdocManager)

**Utilities (`utils/`):**
- `auth.py` - JWT token handling and authentication utilities
- `access_control.py` - Permission and access control logic
- `middleware.py` - Custom middleware (request processing, token tracking)
- `chat.py` - Chat message processing utilities
- `misc.py` - General utility functions
- `oauth.py` - OAuth integration utilities

### Frontend Structure (`src/`)

**Routes (`src/routes/`):**
- `+layout.svelte` - Root layout with auth, i18n, Socket.IO setup, and global state management
- `(app)/` - Main authenticated application routes
  - `(app)/admin/` - Admin dashboard and settings
  - `(app)/c/` - Chat interface
  - `(app)/workspace/` - Workspace/tools interface
  - `(app)/notes/` - Notes feature
  - `(app)/channels/` - Channel/group features
- `auth/` - Authentication pages
- `s/[id]/` - Shared chat views

**Components (`src/lib/components/`):**
- `chat/` - Chat UI components (MessageInput, Messages, etc.)
- `admin/` - Admin panel components (Settings, Users, etc.)
- `workspace/` - Workspace-related components
- `layout/` - Layout components (Sidebar, Navbar, etc.)
- `common/` - Reusable UI components

**API Clients (`src/lib/apis/`):**
- Each API has a corresponding client module (e.g., `chats/`, `openai/`, `users/`)
- These modules handle HTTP requests to backend endpoints

**State Management (`src/lib/stores/`):**
- Svelte stores for global state (user, config, chats, settings, etc.)

**Build Configuration:**
- Uses `@sveltejs/adapter-static` to build static files
- Output goes to `build/` directory
- Backend serves these static files from `static/` via FastAPI StaticFiles

### Request Flow

1. **Frontend** (Svelte) makes API calls to backend via fetch/axios
2. **Backend Middleware** processes request (authentication, logging, token tracking)
3. **FastAPI Router** handles endpoint and calls appropriate function
4. **Database Models** via SQLAlchemy perform CRUD operations
5. **Response** sent back to frontend
6. **Socket.IO** handles real-time updates (chat updates, presence, collaborative editing)

### Key Architecture Patterns

**Reverse Proxy Pattern:**
- `/ollama/*` routes proxy requests to OLLAMA_BASE_URL
- `/openai/*` routes proxy to OpenAI-compatible endpoints
- This prevents CORS issues and adds authentication layer

**Plugin System:**
- Pipelines plugin framework allows custom Python logic integration
- Functions/Tools can be added via UI with built-in code editor
- Tools use RestrictedPython for sandboxed execution

**RAG Integration:**
- Documents loaded into vector databases (ChromaDB default)
- Embedding models run locally or via API
- Retrieved chunks injected into LLM context
- Web search providers integrate for real-time information

**Multi-Model Support:**
- Multiple models can be queried in parallel
- Model routing via middleware
- Token usage tracking per user/group via Socket.IO

**Authentication:**
- JWT-based authentication with configurable OAuth providers
- Role-based access control (RBAC)
- User groups with granular permissions

## Configuration

**Environment Variables:**
- See `backend/open_webui/env.py` for all available environment variables
- Key variables: `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL`
- WebUI behavior: `WEBUI_AUTH`, `ENABLE_WEBSOCKET_SUPPORT`, `WEBSOCKET_MANAGER`

**Database:**
- Default: SQLite at `backend/data/webui.db`
- Supports PostgreSQL and MySQL via `DATABASE_URL`
- Migrations auto-run on startup

**Docker Environment:**
- Set `DOCKER=true` for containerized deployments
- Use `USE_CUDA_DOCKER=true` for GPU support
- `OLLAMA_BASE_URL` must point to accessible Ollama instance

## Development Workflow

1. **Starting Development:**
   - Run backend: `cd backend && ./dev.sh`
   - Run frontend: `npm run dev`
   - Frontend proxies API calls to backend during development

2. **Making Database Changes:**
   - Modify model in `backend/open_webui/models/`
   - Create migration: `alembic revision -m "description"`
   - Edit migration in `backend/open_webui/migrations/versions/`
   - Migration runs automatically on next backend start

3. **Adding API Endpoints:**
   - Add route function in appropriate `backend/open_webui/routers/` file
   - Register router in `backend/open_webui/main.py` if new router
   - Add corresponding API client function in `src/lib/apis/`
   - Use API client in frontend components

4. **Adding Frontend Components:**
   - Create Svelte component in `src/lib/components/`
   - Import and use in routes
   - Follow existing component patterns (props, events, stores)

5. **Working with Socket.IO:**
   - Backend socket events defined in `backend/open_webui/socket/main.py`
   - Frontend socket client initialized in `src/routes/+layout.svelte`
   - Use socket store for emitting/listening to events

## Common Patterns

**Database CRUD:**
```python
# In models/example.py
class ExampleTable:
    def insert_new_example(self, form_data):
        with get_db() as db:
            example = ExampleModel(**form_data.model_dump())
            db.add(example)
            db.commit()
            db.refresh(example)
            return ExampleModel.model_validate(example)
```

**API Router:**
```python
# In routers/example.py
@router.get("/examples")
async def get_examples(user=Depends(get_verified_user)):
    return ExampleTable.get_examples()
```

**Frontend API Call:**
```javascript
// In src/lib/apis/example/index.ts
export const getExamples = async (token: string) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/examples`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return res.json();
};
```

## Code Style

- **Python**: Follow Black formatting (line length 88)
- **JavaScript/Svelte**: Follow Prettier formatting
- **Imports**: Group by standard lib, third-party, local
- **Naming**: snake_case for Python, camelCase for JavaScript

## Token Usage System (Custom Feature)

This codebase includes a token usage tracking and limiting system:
- Models in `backend/open_webui/models/token_usage.py`
- Socket.IO integration in `backend/open_webui/socket/main.py`
- Middleware tracking in `backend/open_webui/utils/middleware.py`
- Frontend UI in `src/lib/components/admin/Settings/ModelLimits.svelte`
- See `TOKEN_USAGE_README.md` for detailed documentation
