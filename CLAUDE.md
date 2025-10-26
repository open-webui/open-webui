# Open WebUI - Architecture Overview

Open WebUI is a full-stack application providing a user interface for interacting with Large Language Models (LLMs). It combines a SvelteKit frontend with a FastAPI backend, featuring real-time communication, document processing for RAG, multi-LLM support, collaborative editing, and extensibility through tools and functions.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (SvelteKit)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Components  │  │    Routes    │  │    Stores    │         │
│  │   (Svelte)   │◄─┤(File-based)  │◄─┤  (Reactive)  │         │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘         │
│         │                                     │                 │
│         └─────────────┬───────────────────────┘                 │
│                       │                                         │
│                  ┌────▼─────┐                                   │
│                  │   APIs   │                                   │
│                  │(HTTP/WS) │                                   │
│                  └────┬─────┘                                   │
└───────────────────────┼─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        │      HTTP     │    WebSocket  │
        │               │               │
┌───────▼───────────────▼───────────────▼─────────────────────────┐
│                     Backend (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Routers    │  │    Socket    │  │    Models    │         │
│  │ (Endpoints)  │  │  (Socket.IO) │  │ (SQLAlchemy) │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └────────┬─────────┴──────────────────┘                 │
│                  │                                               │
│         ┌────────┴────────┐                                     │
│         │                 │                                     │
│    ┌────▼─────┐     ┌────▼────────┐                            │
│    │Retrieval │     │  Internal   │                            │
│    │  (RAG)   │     │(DB/Migrations)│                          │
│    └────┬─────┘     └─────────────┘                            │
│         │                                                       │
└─────────┼───────────────────────────────────────────────────────┘
          │
     ┌────┴────┐
     │         │
┌────▼───┐  ┌─▼──────────┐
│Vector  │  │   LLM      │
│  DB    │  │ Providers  │
│(8 types)│  │(OpenAI,    │
└─────────┘  │Ollama, etc)│
             └────────────┘
```

## Core Components

### Frontend (src/)
**Technology:** SvelteKit (SPA mode, no SSR)

**Key Directories:**
- **`src/lib/components/`** - Svelte UI components
  - `admin/` - Admin panel components (user management, system config)
  - `chat/` - Chat interface (Messages, MessageInput, ModelSelector)
  - `workspace/` - Resource management (Files, Knowledge, Tools, Prompts)
  - `common/` - Reusable components (Modal, Toast, Dropdown, etc.)
  - `layout/` - App shell (Navbar, Sidebar, Footer)

- **`src/lib/stores/`** - Reactive state management
  - 40+ Svelte writable stores (user, models, chats, settings, UI state)
  - Auto-subscription pattern for reactive updates
  - Initialized in `routes/(app)/+layout.svelte`

- **`src/lib/apis/`** - Backend API abstraction layer
  - TypeScript wrappers for all HTTP endpoints
  - Authentication via JWT in headers
  - Streaming support for chat completions
  - 16+ API modules (chats, users, files, retrieval, models, etc.)

- **`src/routes/`** - File-based routing
  - `(app)/` - Authenticated routes with shared layout
  - `(app)/c/[id]/` - Individual chat routes
  - `(app)/admin/` - Admin panel (role='admin' required)
  - `(app)/workspace/` - User workspace
  - `auth/` - Sign in/sign up (unauthenticated)
  - `s/[id]/` - Public shared chats

**Integration Pattern:**
```
User Interaction → Component → API Call → Store Update → UI Re-render
                                    ↓
                           Backend HTTP/WebSocket
```

### Backend (backend/open_webui/)
**Technology:** FastAPI with SQLAlchemy ORM

**Key Directories:**
- **`routers/`** - REST API endpoints
  - `auths.py` - Authentication (signin, signup, session)
  - `chats.py` - Chat CRUD, sharing, tagging
  - `files.py` - File upload, download, deletion
  - `models.py` - Model management
  - `retrieval.py` - RAG processing and querying
  - `knowledge.py` - Knowledge base management
  - `tools.py`, `functions.py` - Extensibility
  - `openai.py`, `ollama.py` - LLM proxies

- **`models/`** - Database ORM models
  - 18+ model files (User, Chat, File, Knowledge, Tool, etc.)
  - DAO/Repository pattern with singleton instances
  - JSON fields for flexible schemas
  - Access control integration

- **`socket/`** - WebSocket communication
  - Socket.IO server for real-time events
  - Session management (SESSION_POOL, USER_POOL)
  - Collaborative editing via Yjs/CRDT
  - Token usage tracking
  - Chat event streaming

- **`retrieval/`** - RAG pipeline
  - `loaders/` - Document processing (PDF, Word, Excel, HTML, etc.)
  - `vector/` - Vector database abstraction (8 backends)
  - `web/` - Web search integration (21 providers)
  - `utils.py` - Embedding generation, semantic search

- **`internal/`** - Database infrastructure
  - `db.py` - SQLAlchemy engine, session management
  - `wrappers.py` - Peewee compatibility (legacy migrations)
  - `migrations/` - Alembic migration files

**Integration Pattern:**
```
HTTP Request → Router → Model (DB) → Response
                  ↓
         Optional: Socket Emit → Frontend
                  ↓
         Optional: Vector DB Query → RAG Context
```

## Data Flow Patterns

### Authentication Flow
```
1. User submits credentials (frontend: auth/+page.svelte)
2. Frontend: signinUser(email, password) → POST /api/auths/signin
3. Backend: routers/auths.py validates credentials via models/auths.py
4. Backend returns { token (JWT), user }
5. Frontend: localStorage.token = token, user.set(userData)
6. Frontend: goto('/') → App layout initializes stores
7. All subsequent requests include: Authorization: Bearer {token}
```

### Chat Message Flow
```
1. User types message (frontend: MessageInput.svelte)
2. Frontend: createNewChat() → POST /api/chats/new
3. Backend: routers/chats.py creates chat in models/chats.py
4. Frontend: generateOpenAIChatCompletion() → POST /api/chat/completions
5. Backend: routers/openai.py proxies to LLM provider
6. Backend streams response via Socket.IO 'chat-events'
7. Frontend: Messages.svelte receives chunks, renders token-by-token
8. On completion: Chat saved, sidebar updated
```

### RAG Document Processing Flow
```
1. User uploads file (frontend: Files.svelte)
2. Frontend: uploadFile() → POST /api/files (multipart/form-data)
3. Backend: routers/files.py saves via storage/provider.py
4. Backend: models/files.py creates database record
5. Frontend: processFile() → POST /api/retrieval/process/file
6. Backend: retrieval/loaders/main.py extracts text
7. Backend: Text chunked (RecursiveCharacterTextSplitter)
8. Backend: retrieval/utils.py generates embeddings
9. Backend: retrieval/vector/factory.py VECTOR_DB_CLIENT.insert()
10. File embedded in vector database, ready for queries
```

### RAG Query Flow
```
1. User enables file in chat (frontend: MessageInput.svelte)
2. User sends message
3. Backend: retrieval/utils.py get_sources_from_items()
4. Backend: Embeds query text
5. Backend: VECTOR_DB_CLIENT.search() → Top-k chunks
6. Backend: Chunks formatted and added to system prompt
7. Backend: LLM receives query + relevant context
8. LLM generates response with grounded information
```

### WebSocket Real-Time Updates
```
1. Backend emits event: get_event_emitter()({ type: 'chat:completion', data: {...} })
2. socket/main.py broadcasts to user's sessions via USER_POOL
3. Frontend: $socket.on('chat-events', handleEvent)
4. Frontend: Messages.svelte updates message state
5. UI re-renders with new content (all tabs synchronized)
```

## Critical Integration Points

### Frontend ↔ Backend (HTTP)
- **Endpoint Mapping:** `src/lib/apis/chats/index.ts` → `backend/routers/chats.py`
- **Authentication:** All requests include `Authorization: Bearer {token}` header
- **Data Format:** JSON request/response bodies
- **Error Handling:** HTTP status codes + error messages in response text

### Frontend ↔ Backend (WebSocket)
- **Connection:** `src/lib/stores/index.ts` initializes Socket.IO client
- **Authentication:** JWT token in socket auth handshake
- **Events:** 'chat-events', 'channel-events', 'ydoc:document:*', 'usage'
- **Handlers:** Components subscribe via `$socket.on(event, handler)`

### Backend ↔ Database
- **ORM:** SQLAlchemy declarative models
- **Session Management:** `get_db()` context manager
- **Migrations:** Alembic for schema evolution
- **Connection Pooling:** Configurable via DATABASE_POOL_SIZE

### Backend ↔ Vector Database
- **Abstraction:** `retrieval/vector/factory.py` VECTOR_DB_CLIENT
- **Backends:** Chroma, Qdrant, Pinecone, Milvus, Elasticsearch, OpenSearch, PgVector
- **Operations:** insert(), search(), query(), delete_collection()
- **Configuration:** VECTOR_DB environment variable

### Backend ↔ LLM Providers
- **Proxying:** `routers/openai.py`, `routers/ollama.py`
- **Streaming:** Async generators for SSE responses
- **Configuration:** Model parameters, system prompts, temperature, etc.
- **Error Handling:** Retry logic, fallback models

## State Management

### Frontend State (Svelte Stores)
- **Global:** `$lib/stores/index.ts` (user, models, chats, settings, etc.)
- **Initialization:** `routes/(app)/+layout.svelte` onMount
- **Persistence:** localStorage for token, backend API for user data
- **Synchronization:** WebSocket events keep stores in sync

### Backend State (Database)
- **Persistent:** PostgreSQL or SQLite via SQLAlchemy
- **Session:** Redis-backed session management for WebSocket (multi-instance)
- **Cache:** No HTTP caching; stores act as client-side cache

### Real-Time State (WebSocket)
- **SESSION_POOL:** Socket ID → User object
- **USER_POOL:** User ID → Socket IDs (multi-tab support)
- **YDOC_MANAGER:** Yjs document state for collaborative editing
- **USAGE_POOL:** Token usage tracking with periodic cleanup

## Key Workflows

### Initial App Load
```
1. User visits / → SvelteKit routes to (app)/+page.svelte
2. (app)/+layout.svelte onMount:
   - Check localStorage.token (redirect to /auth if missing)
   - getSessionUser() → user store
   - Parallel API calls: getModels(), getTools(), getKnowledgeBases(), etc.
   - Initialize Socket.IO connection
3. +page.svelte renders chat interface
4. Components subscribe to stores, UI renders with data
```

### Create Chat + Send Message
```
1. MessageInput: User types message
2. createNewChat() → POST /api/chats/new
3. Backend creates chat, returns { id, title, messages }
4. chats.update(c => [newChat, ...c]) → Sidebar updates
5. generateOpenAIChatCompletion() → POST /api/chat/completions
6. Backend streams response via Socket.IO
7. Messages.svelte receives 'chat-events', renders chunks
8. On completion: Chat saved, title generated (if needed)
```

### Admin User Management
```
1. Admin visits /admin/settings → Users.svelte
2. getUsers() → GET /api/users
3. Admin clicks "Edit" → Modal opens
4. Admin changes role to 'admin'
5. updateUserById() → POST /api/users/{id}/update
6. Backend updates user record
7. Component refreshes user list, shows updated role
```

### Knowledge Base Query
```
1. User creates knowledge base → POST /api/knowledge
2. User adds files → POST /api/knowledge/{id}/file/add
3. Backend processes each file:
   - Loader extracts text
   - Chunks and embeds
   - Stores in vector DB under knowledge_id collection
4. User enables KB in chat → selectedKnowledge store updated
5. User sends message
6. Backend: queryCollection([knowledge_id], query)
7. Top-k chunks retrieved, added to system prompt
8. LLM generates response with context
```

## Technology Stack

### Frontend
- **Framework:** SvelteKit 1.x (SPA mode)
- **Language:** TypeScript
- **State Management:** Svelte writable stores
- **Styling:** TailwindCSS
- **Real-Time:** Socket.IO client
- **Markdown:** svelte-markdown + highlight.js
- **Build:** Vite

### Backend
- **Framework:** FastAPI 0.1x+
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.x + Alembic
- **Database:** PostgreSQL or SQLite
- **Real-Time:** Socket.IO (Python)
- **RAG:** LangChain, sentence-transformers
- **Vector DBs:** Chroma, Qdrant, Pinecone, Milvus, Elasticsearch, OpenSearch, PgVector
- **Web Server:** Uvicorn (ASGI)

### Infrastructure
- **Authentication:** JWT (HS256)
- **Session Storage:** Redis (optional, for distributed deployments)
- **File Storage:** Local filesystem or S3-compatible cloud storage
- **Observability:** OpenTelemetry (optional)

## Directory Structure Reference

```
open-webui/
├── backend/
│   ├── open_webui/
│   │   ├── routers/          # FastAPI endpoints
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── socket/           # WebSocket handlers
│   │   ├── retrieval/        # RAG pipeline
│   │   │   ├── loaders/      # Document processing
│   │   │   ├── vector/       # Vector DB abstraction
│   │   │   └── web/          # Web search
│   │   ├── internal/         # Database infrastructure
│   │   │   └── migrations/   # Alembic migrations
│   │   ├── storage/          # File storage provider
│   │   └── utils/            # Shared utilities
│   └── tests/                # Pytest test suite
├── src/
│   ├── lib/
│   │   ├── apis/             # Backend API wrappers
│   │   ├── components/       # Svelte components
│   │   │   ├── admin/        # Admin panel
│   │   │   ├── chat/         # Chat interface
│   │   │   ├── workspace/    # Resource management
│   │   │   ├── common/       # Reusable components
│   │   │   └── layout/       # App shell
│   │   ├── stores/           # Reactive state
│   │   └── utils/            # Frontend utilities
│   └── routes/               # SvelteKit file-based routing
│       ├── (app)/            # Authenticated routes
│       │   ├── c/[id]/       # Individual chats
│       │   ├── admin/        # Admin panel
│       │   └── workspace/    # User workspace
│       ├── auth/             # Sign in/up
│       └── s/[id]/           # Public shared chats
└── CLAUDE.md files in each directory for detailed documentation
```

## Important Architectural Decisions

### Why SvelteKit (SPA Mode)?
- **Reactive State:** Svelte's stores provide simple, performant state management
- **File-Based Routing:** Intuitive URL structure
- **No SSR:** Backend API separation, simpler deployment
- **Small Bundle:** Svelte compiles to vanilla JS, minimal runtime

### Why FastAPI?
- **Performance:** Async/await for high concurrency
- **Type Safety:** Pydantic models for request/response validation
- **Auto Docs:** OpenAPI/Swagger UI generation
- **WebSocket Support:** Native async WebSocket handling

### Why SQLAlchemy?
- **Flexibility:** Supports PostgreSQL and SQLite
- **Migrations:** Alembic for schema evolution
- **Type Safety:** Declarative models with Python type hints
- **Connection Pooling:** Built-in for production

### Why Socket.IO?
- **Reliability:** Auto-reconnection, fallback to long-polling
- **Room Support:** Channel and document collaboration
- **Event-Based:** Clean pub/sub pattern
- **Cross-Tab Sync:** Multiple sessions per user

### Why Multiple Vector DB Backends?
- **Flexibility:** Users choose based on scale/deployment
- **Performance:** Different backends optimized for different use cases
- **Vendor Lock-In Avoidance:** Unified interface abstracts backend

## Configuration & Deployment

### Environment Variables (Backend)
- `DATABASE_URL` - PostgreSQL or SQLite connection string
- `VECTOR_DB` - Vector database type (chroma, qdrant, pinecone, etc.)
- `RAG_EMBEDDING_ENGINE` - Embedding model (local, openai, azure, ollama)
- `WEBUI_SECRET_KEY` - JWT signing key
- `WEBSOCKET_MANAGER` - redis or memory
- `OPENAI_API_KEY`, `OLLAMA_BASE_URL` - LLM provider configuration

### Environment Variables (Frontend)
- `PUBLIC_API_BASE_URL` - Backend API URL (for production builds)

### Deployment Patterns
- **Single Server:** SQLite, in-memory sessions, local files
- **Distributed:** PostgreSQL, Redis sessions, S3 storage
- **Docker Compose:** Provided docker-compose.yaml with all services
- **Kubernetes:** Scalable deployment with Redis and PostgreSQL

## Security Considerations

### Authentication
- **JWT Tokens:** Stored in localStorage (vulnerable to XSS)
- **Token Expiration:** Configurable via JWT_EXPIRES_IN
- **No Refresh Tokens:** Long-lived JWTs (security concern)

### Authorization
- **Role-Based:** user.role ('user', 'pending', 'admin')
- **Permission-Based:** user.permissions object (workspace, chat, etc.)
- **API-Level Enforcement:** Backend validates all requests
- **Client-Side Guards:** Route guards for UX (not security)

### Data Protection
- **Password Hashing:** bcrypt via passlib
- **SQL Injection:** Prevented by SQLAlchemy ORM
- **XSS:** Svelte auto-escaping, DOMPurify for markdown
- **CSRF:** Not applicable (stateless JWT auth)
- **File Upload:** Extension whitelist, size limits

## Testing Strategy

### Backend Tests (`backend/tests/`)
- **Unit Tests:** Individual functions and models
- **API Tests:** Endpoint request/response validation
- **Integration Tests:** Full workflows (signup → chat → completion)
- **Mocking:** External services (LLM APIs, vector DBs)
- **Coverage:** Target >80% for critical paths

### Test Execution
```bash
pytest backend/tests/               # All tests
pytest --cov=open_webui             # With coverage
pytest -n auto                      # Parallel execution
pytest -m integration               # Integration tests only
```

## Performance Considerations

### Frontend
- **Virtual Scrolling:** Long chat histories (Messages.svelte)
- **Debounced Search:** Reduce API calls
- **Lazy Loading:** Modal content, images
- **Store Optimization:** Minimize unnecessary updates

### Backend
- **Connection Pooling:** Database and HTTP connections
- **Async Endpoints:** FastAPI async/await for concurrency
- **Streaming Responses:** Chat completions via SSE
- **Background Tasks:** File processing, embedding generation
- **Caching:** No HTTP cache (consider adding for static config)

### Database
- **Indexes:** On frequently queried columns (user_id, chat_id)
- **Pagination:** Large result sets (chats, users)
- **Bulk Operations:** Batch inserts for embeddings
- **Connection Limits:** Pool size tuning

## Extensibility

### Tools & Functions
- **Custom Tools:** Python modules with execute() function
- **Valves:** Configuration parameters (global + per-user)
- **Tool Discovery:** Auto-loaded from models/tools.py
- **Sandboxing:** Execution isolation (security concern)

### LLM Providers
- **Plugin Pattern:** New providers via routers/
- **Configuration:** Model parameters, endpoints, API keys
- **Fallback:** Multiple providers for reliability

### Vector Databases
- **Abstraction:** VectorDBBase interface
- **New Backends:** Implement search(), insert(), delete_collection()
- **Factory Pattern:** get_vector() selects backend

## Monitoring & Observability

### Logging
- **Backend:** Python logging module
- **Frontend:** console.log (consider structured logging)
- **Levels:** DEBUG, INFO, WARNING, ERROR

### Metrics (Optional)
- **OpenTelemetry:** Traces and metrics
- **Token Usage:** Tracked via socket events
- **Active Users:** SESSION_POOL size

### Error Tracking
- **Backend Exceptions:** Logged to stdout/files
- **Frontend Errors:** window.onerror, console.error
- **Consider:** Sentry or similar service

## Documentation

Each major directory contains a `CLAUDE.md` file with detailed architectural documentation:

- **Backend:**
  - `backend/open_webui/models/CLAUDE.md` - Database models
  - `backend/open_webui/routers/CLAUDE.md` - API endpoints
  - `backend/open_webui/socket/CLAUDE.md` - WebSocket communication
  - `backend/open_webui/retrieval/CLAUDE.md` - RAG pipeline
  - `backend/open_webui/internal/CLAUDE.md` - Database infrastructure
  - `backend/tests/CLAUDE.md` - Test suite

- **Frontend:**
  - `src/lib/stores/CLAUDE.md` - State management
  - `src/lib/apis/CLAUDE.md` - API abstraction
  - `src/lib/components/CLAUDE.md` - UI components
  - `src/routes/CLAUDE.md` - Routing system

These files provide in-depth information on:
- Component purposes and responsibilities
- Integration points and dependencies
- Data flow patterns
- Key workflows
- Important architectural decisions
