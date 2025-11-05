# Open WebUI - Technical Architecture Documentation

> **Version:** 0.6.34
> **Last Updated:** 2025-11-05
> **Maintained by:** Open WebUI Team

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. System Architecture Overview](#2-system-architecture-overview)
- [3. Technology Stack](#3-technology-stack)
- [4. Frontend Architecture](#4-frontend-architecture)
- [5. Backend Architecture](#5-backend-architecture)
- [6. Database Architecture](#6-database-architecture)
- [7. RAG (Retrieval Augmented Generation) System](#7-rag-retrieval-augmented-generation-system)
- [8. Real-Time Communication](#8-real-time-communication)
- [9. Authentication & Authorization](#9-authentication--authorization)
- [10. Plugin & Extension System](#10-plugin--extension-system)
- [11. AI/ML Integration Layer](#11-aiml-integration-layer)
- [12. Storage Architecture](#12-storage-architecture)
- [13. Deployment Architecture](#13-deployment-architecture)
- [14. Security Architecture](#14-security-architecture)
- [15. Scalability & Performance](#15-scalability--performance)
- [16. Integration Points](#16-integration-points)

---

## 1. Executive Summary

Open WebUI is an **extensible, feature-rich, self-hosted AI platform** that operates entirely offline while supporting various LLM runners (Ollama, OpenAI-compatible APIs) and includes a built-in inference engine for RAG operations.

### Key Architectural Characteristics

- **Hybrid Architecture**: SvelteKit frontend + FastAPI backend
- **Database-Agnostic**: Supports SQLite, PostgreSQL, MySQL
- **Multi-Model**: Simultaneous interaction with multiple LLMs
- **Real-Time**: WebSocket-based collaboration and streaming
- **Extensible**: Pipeline plugin system + custom Python functions
- **Enterprise-Ready**: RBAC, SCIM 2.0, LDAP, OAuth2
- **Scalable**: Redis-backed sessions, cloud storage, vector DB options

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │  Mobile PWA  │  │ Desktop App  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                            ↓ HTTPS/WSS
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER (SvelteKit)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Pages & Routes                                           │   │
│  │  • Chat UI (c/[id])      • Workspace (models/prompts)   │   │
│  │  • Admin Panel           • Knowledge Base               │   │
│  │  • Notes (Collaboration) • Authentication               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ State Management (Svelte Stores)                         │   │
│  │  • User State  • Config  • Socket  • Theme  • Mobile    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ API Client Layer (TypeScript)                            │   │
│  │  • auth, chats, models, knowledge, retrieval, etc.      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                    ↓ REST API (JSON) + WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND LAYER (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ API Gateway & Routing (26 Router Modules)                │   │
│  │  /api/auths    /api/chats      /api/models               │   │
│  │  /api/knowledge /api/retrieval /api/functions            │   │
│  │  /api/users     /api/configs   /api/pipelines            │   │
│  │  ... and 18 more routers                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Business Logic Layer                                      │   │
│  │  • Models (ORM)  • Utils  • Services  • Middleware      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Integration Services                                      │   │
│  │  • RAG Engine    • Auth Manager  • Storage Provider     │   │
│  │  • Socket.IO     • MCP Client    • Plugin System        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐    │
│  │   Database    │  │  File Storage │  │   Vector DBs     │    │
│  │ SQLite/PG/SQL │  │ Local/S3/Azure│  │ Chroma/Qdrant/.. │    │
│  └───────────────┘  └───────────────┘  └──────────────────┘    │
│  ┌───────────────┐  ┌───────────────┐                           │
│  │  Redis Cache  │  │   Sessions    │                           │
│  └───────────────┘  └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Ollama    │  │ OpenAI APIs  │  │  OAuth IdP   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Web Search   │  │   LDAP/AD    │  │  SCIM Server │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Directory Structure

```
Badri-OWUI/
├── src/                              # Frontend (SvelteKit + TypeScript)
│   ├── lib/
│   │   ├── apis/                    # API client services
│   │   ├── components/              # Reusable UI components
│   │   ├── stores/                  # Svelte state stores
│   │   ├── types/                   # TypeScript types
│   │   ├── utils/                   # Utility functions
│   │   ├── workers/                 # Web Workers
│   │   ├── i18n/                    # Internationalization (40+ languages)
│   │   └── pyodide/                 # Python runtime (Pyodide)
│   └── routes/                      # SvelteKit pages
│       ├── (app)/                   # Protected routes
│       │   ├── admin/              # Admin panel
│       │   ├── workspace/          # Models, prompts, functions, knowledge
│       │   ├── playground/         # Chat playground
│       │   ├── notes/              # Collaborative notes
│       │   └── c/[id]/             # Chat conversations
│       ├── auth/                    # Authentication flows
│       └── s/                       # Shared/published content
│
├── backend/                         # Backend (Python + FastAPI)
│   └── open_webui/
│       ├── main.py                 # FastAPI app entry point
│       ├── config.py               # Configuration (110KB)
│       ├── models/                 # SQLAlchemy ORM models
│       ├── routers/                # API route handlers (26 modules)
│       ├── retrieval/              # RAG system
│       │   ├── loaders/           # Document loaders
│       │   ├── vector/            # Vector DB abstraction
│       │   └── web/               # Web search integration
│       ├── socket/                 # WebSocket server (Socket.IO)
│       ├── storage/                # File storage abstraction
│       ├── utils/                  # Utilities
│       │   ├── auth.py            # Auth utilities
│       │   ├── plugin.py          # Plugin system
│       │   ├── mcp/               # MCP client
│       │   └── middleware.py      # Request middleware
│       ├── internal/               # Internal DB/migrations
│       └── migrations/             # Alembic migrations
│
├── static/                          # Public assets
├── docs/                            # Documentation
├── kubernetes/                      # K8s configs
├── .github/workflows/               # CI/CD
├── pyproject.toml                   # Python dependencies (120+ packages)
└── package.json                     # Node.js dependencies
```

---

## 3. Technology Stack

### 3.1 Frontend Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | SvelteKit | 2.5.20 | SSR/SSG web framework |
| **Language** | TypeScript | 5.5.4 | Type-safe JavaScript |
| **Build Tool** | Vite | 5.4.14 | Fast bundler & dev server |
| **UI Framework** | TailwindCSS | 4.0.0 | Utility-first CSS |
| **UI Components** | Bits UI | 0.21.15 | Headless UI library |
| **State Management** | Svelte Stores | Built-in | Reactive state |
| **Rich Text Editor** | Tiptap | 3.0.7 | Extensible editor |
| **Code Editor** | CodeMirror | 6.0.1 | In-browser code editor |
| **Charts** | Chart.js | 4.5.0 | Data visualization |
| **Diagrams** | Mermaid | 11.10.1 | Markdown diagrams |
| **i18n** | i18next | 23.10.0 | Internationalization |
| **Real-time** | Socket.io-client | 4.2.0 | WebSocket client |
| **Collaboration** | Yjs | 13.6.27 | CRDT for real-time sync |
| **Python Runtime** | Pyodide | 0.28.2 | Python in browser |
| **Testing** | Vitest + Cypress | 1.6.1 / 13.15.0 | Unit + E2E tests |

### 3.2 Backend Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.118.0 | Async web framework |
| **Server** | Uvicorn | 0.37.0 | ASGI server |
| **Language** | Python | 3.11-3.12 | Backend language |
| **ORM** | SQLAlchemy | 2.0.38 | Database ORM |
| **Migrations** | Alembic | 1.14.0 | Schema migrations |
| **WebSocket** | Python-SocketIO | 5.13.0 | Real-time server |
| **Authentication** | PyJWT | 2.9.0 | JWT tokens |
| **Password Hashing** | bcrypt | 4.2.1 | Secure hashing |
| **HTTP Client** | aiohttp | 3.11.11 | Async HTTP |
| **Caching** | aiocache | 0.12.3 | Async cache |
| **Jobs** | APScheduler | 3.11.0 | Background tasks |
| **Validation** | Pydantic | 2.10.6 | Data validation |
| **Logging** | Loguru | 0.7.3 | Structured logging |

### 3.3 AI/ML Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Embeddings** | Sentence-Transformers | 3.3.1 | Text embeddings |
| **Transformers** | Hugging Face Transformers | 4.48.3 | Model inference |
| **Vector DB (Default)** | ChromaDB | 0.6.4 | Vector storage |
| **Document Parsing** | pypdf | 5.1.0 | PDF processing |
| **Web Scraping** | BeautifulSoup4 | 4.12.3 | HTML parsing |
| **OCR** | rapidocr-onnxruntime | 1.3.27 | Image text extraction |
| **Speech-to-Text** | Faster Whisper | 1.1.0 | Audio transcription |
| **OpenAI SDK** | openai | 1.59.7 | OpenAI API client |
| **Anthropic SDK** | anthropic | 0.42.0 | Claude API client |
| **Google AI** | google-generativeai | 0.8.3 | Gemini API |
| **LangChain** | langchain | 0.3.14 | LLM orchestration |
| **Code Execution** | RestrictedPython | 7.4 | Safe Python sandbox |

### 3.4 Database & Storage

| Type | Options | Default |
|------|---------|---------|
| **Relational DB** | SQLite, PostgreSQL, MySQL | SQLite (WAL) |
| **Vector DB** | Chroma, Qdrant, Milvus, Pinecone, PgVector, OpenSearch, Elasticsearch, S3Vector, Oracle23ai | ChromaDB |
| **Cache** | Redis, in-memory | In-memory |
| **File Storage** | Local, AWS S3, Azure Blob, GCP Storage | Local |
| **Session Store** | Redis, database | Database |

---

## 4. Frontend Architecture

### 4.1 SvelteKit Structure

Open WebUI uses **SvelteKit** with the **adapter-static** configuration for static site generation with client-side routing fallback.

#### Key Characteristics:
- **SSG + SPA Hybrid**: Pre-rendered static pages with dynamic client-side navigation
- **File-Based Routing**: Routes map directly to file structure
- **Layout System**: Shared layouts with route groups
- **Server-Side Rendering**: Optional SSR for SEO/performance

### 4.2 Route Organization

```
src/routes/
├── +layout.svelte              # Root layout (auth check, theme, i18n)
├── +page.svelte                # Homepage (redirects to /c/new)
│
├── (app)/                      # Protected routes (requires auth)
│   ├── +layout.svelte         # App shell (sidebar, header)
│   ├── c/[id]/                # Chat conversation
│   │   └── +page.svelte       # Chat UI
│   ├── playground/            # Model playground
│   ├── workspace/             # Workspace routes
│   │   ├── models/           # Model management
│   │   ├── prompts/          # Prompt library
│   │   ├── functions/        # Custom functions
│   │   └── knowledge/        # Knowledge base
│   ├── admin/                # Admin panel
│   │   ├── settings/        # System settings
│   │   ├── users/           # User management
│   │   └── knowledge/       # Global knowledge
│   └── notes/               # Collaborative notes
│
├── auth/                      # Authentication
│   ├── signin/              # Login page
│   └── signup/              # Registration
│
└── s/                        # Shared/public content
    └── [shareId]/           # Shared chats
```

### 4.3 State Management

Open WebUI uses **Svelte Writable Stores** for global state:

```typescript
// src/lib/stores/index.ts

// Core Stores
export const user = writable<SessionUser | undefined>(undefined);
export const config = writable<Config | undefined>(undefined);
export const socket = writable<Socket | null>(null);
export const theme = writable<'light' | 'dark' | 'system'>('system');
export const mobile = writable<boolean>(false);

// Chat State
export const chatId = writable<string | null>(null);
export const selectedModels = writable<string[]>([]);
export const messages = writable<Message[]>([]);

// Active Users (Real-time Presence)
export const activeUserIds = writable<string[]>([]);

// Usage Tracking
export const USAGE_POOL = writable<Record<string, UsageInfo>>({});
```

**Benefits:**
- Reactive updates across components
- Simple subscription model
- No boilerplate
- Built-in TypeScript support

### 4.4 Component Architecture

```
src/lib/components/
├── admin/                    # Admin panel components
│   ├── Settings/            # System settings UI
│   ├── Users/               # User management UI
│   └── Knowledge/           # Knowledge admin UI
│
├── chat/                    # Chat interface
│   ├── Messages/           # Message rendering
│   │   ├── CodeBlock.svelte
│   │   ├── Markdown.svelte
│   │   └── ContentRenderer.svelte
│   ├── MessageInput/       # Chat input
│   ├── ModelSelector/      # Model selection
│   └── ChatControls/       # Chat actions
│
├── notes/                   # Notes editor
│   ├── Editor.svelte       # Tiptap editor wrapper
│   └── Collaboration.svelte # Yjs integration
│
├── workspace/              # Workspace components
│   ├── Models/            # Model cards
│   ├── Prompts/           # Prompt browser
│   ├── Functions/         # Function editor
│   └── Knowledge/         # Knowledge UI
│
└── common/                # Shared components
    ├── Modal.svelte
    ├── Sidebar.svelte
    ├── Tooltip.svelte
    └── Dropdown.svelte
```

### 4.5 API Client Layer

TypeScript API clients abstract backend communication:

```typescript
// src/lib/apis/chats/index.ts
export const getChatList = async (token: string) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/chats/`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` }
  });
  return res.json();
};

export const getChatById = async (token: string, id: string) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` }
  });
  return res.json();
};

// Streaming support
export const streamChat = async (
  token: string,
  payload: ChatRequest,
  onMessage: (data: any) => void
) => {
  const eventSource = new EventSource(
    `${WEBUI_API_BASE_URL}/chats/stream`,
    { headers: { Authorization: `Bearer ${token}` } }
  );

  eventSource.onmessage = (e) => onMessage(JSON.parse(e.data));
  return eventSource;
};
```

### 4.6 Real-Time Features

#### Socket.IO Integration

```typescript
// src/lib/socket.ts
import { io, Socket } from 'socket.io-client';

export const connectSocket = (token: string): Socket => {
  const socket = io(WEBUI_API_BASE_URL, {
    auth: { token },
    transports: ['websocket', 'polling']
  });

  socket.on('connect', () => console.log('Connected'));
  socket.on('message', handleMessage);
  socket.on('user_join', handleUserJoin);

  return socket;
};
```

#### Yjs Collaboration (Notes)

```typescript
// Notes use Yjs CRDT for conflict-free real-time editing
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';

const ydoc = new Y.Doc();
const provider = new WebsocketProvider(
  'ws://localhost:8080',
  'note-' + noteId,
  ydoc
);
```

---

## 5. Backend Architecture

### 5.1 FastAPI Application Structure

**Entry Point:** `backend/open_webui/main.py`

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import socketio

# FastAPI app
app = FastAPI(title="Open WebUI API", version="0.6.34")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
from open_webui.internal.db import init_db
init_db()

# Register routers (26 modules)
from open_webui.routers import (
    auths, users, chats, models, knowledge, retrieval,
    functions, tools, prompts, files, folders, configs,
    # ... and 14 more
)

app.include_router(auths.router, prefix="/api", tags=["auths"])
app.include_router(chats.router, prefix="/api", tags=["chats"])
# ... include all routers

# Socket.IO integration
from open_webui.socket.main import get_socket_manager
sio = get_socket_manager()
socket_app = socketio.ASGIApp(sio, app)

# Serve static files (built frontend)
app.mount("/", StaticFiles(directory="static", html=True))
```

### 5.2 API Router Architecture

Each router module handles a specific domain:

```
backend/open_webui/routers/
├── auths.py              # Authentication (login, signup, sessions)
├── users.py              # User CRUD and management
├── chats.py              # Chat operations
├── messages.py           # Message operations
├── models.py             # Model management
├── ollama.py             # Ollama-specific endpoints
├── openai.py             # OpenAI-compatible API
├── retrieval.py          # RAG queries
├── knowledge.py          # Knowledge base management
├── files.py              # File upload/download
├── functions.py          # Custom function management
├── tools.py              # External tool management
├── prompts.py            # Prompt library
├── configs.py            # System configuration
├── pipelines.py          # Plugin middleware
├── audio.py              # Text-to-speech
├── images.py             # Image generation
├── tasks.py              # Background tasks
├── memories.py           # User memories
├── notes.py              # Note operations
├── folders.py            # Folder organization
├── channels.py           # Channel management
├── groups.py             # User groups
├── evaluations.py        # Model evaluations
├── scim.py               # SCIM 2.0 provisioning
└── utils.py              # Utility endpoints
```

### 5.3 Request Flow

```
1. HTTP Request arrives at FastAPI
   ↓
2. Middleware processing:
   - CORS headers
   - Compression (gzip)
   - Rate limiting
   - Audit logging
   ↓
3. Router matches endpoint
   ↓
4. Dependency injection (auth, DB session)
   ↓
5. Route handler executes
   ↓
6. ORM models interact with database
   ↓
7. Response serialization (Pydantic)
   ↓
8. Response sent to client
```

### 5.4 Dependency Injection Pattern

FastAPI uses **Depends()** for clean dependency injection:

```python
from fastapi import Depends, HTTPException
from open_webui.utils.auth import get_current_user
from open_webui.models.users import Users

@router.get("/chats/")
async def get_chats(
    user: Users = Depends(get_current_user)  # Auth dependency
):
    # user is automatically injected, or 401 if invalid token
    chats = Chats.get_chats_by_user_id(user.id)
    return chats
```

**Common Dependencies:**
- `get_current_user()`: JWT auth validation
- `get_admin_user()`: Admin-only routes
- `get_db_session()`: Database session
- `get_verified_user()`: Email verification check

---

## 6. Database Architecture

### 6.1 Supported Databases

Open WebUI is **database-agnostic** via SQLAlchemy:

| Database | Use Case | Connection String |
|----------|----------|-------------------|
| **SQLite** | Default, single-server | `sqlite:///data/webui.db` |
| **PostgreSQL** | Production, scalable | `postgresql://user:pass@host/db` |
| **MySQL** | Alternative production DB | `mysql://user:pass@host/db` |

**Configuration:** Set via `DATABASE_URL` environment variable.

### 6.2 Core Database Models

**Location:** `backend/open_webui/models/`

```python
# Users & Authentication
class User(Base):
    __tablename__ = "user"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    role = Column(String)  # 'admin', 'user', 'pending'
    profile_image_url = Column(Text)
    api_key = Column(String, unique=True, nullable=True)
    created_at = Column(Integer)
    updated_at = Column(Integer)
    last_active_at = Column(Integer)
    settings = Column(JSON)
    info = Column(JSON)
    oauth_sub = Column(Text, unique=True, nullable=True)

# Chats
class Chat(Base):
    __tablename__ = "chat"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    title = Column(Text)
    chat = Column(JSON)  # Full conversation history
    created_at = Column(Integer)
    updated_at = Column(Integer)
    share_id = Column(String, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    pinned = Column(Boolean, default=False)
    folder_id = Column(String, ForeignKey("folder.id"), nullable=True)
    meta = Column(JSON)

# Knowledge Base
class Knowledge(Base):
    __tablename__ = "knowledge"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(Text)
    description = Column(Text)
    data = Column(JSON)  # File IDs, metadata
    meta = Column(JSON)  # Vector DB info
    created_at = Column(Integer)
    updated_at = Column(Integer)
    access_control = Column(JSON)  # Fine-grained permissions

# Files
class File(Base):
    __tablename__ = "file"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    hash = Column(String)
    filename = Column(Text)
    path = Column(Text)  # Storage path
    data = Column(JSON)  # Metadata (OCR, extraction)
    meta = Column(JSON)
    created_at = Column(Integer)

# Functions
class Function(Base):
    __tablename__ = "function"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(Text)
    type = Column(Text)  # 'function', 'filter', 'action'
    content = Column(Text)  # Python code
    meta = Column(JSON)
    valves = Column(JSON)  # Configuration values
    is_active = Column(Boolean, default=True)
    is_global = Column(Boolean, default=False)

# Prompts
class Prompt(Base):
    __tablename__ = "prompt"
    command = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    title = Column(Text)
    content = Column(Text)

# Notes (with Yjs CRDT)
class Note(Base):
    __tablename__ = "note"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    title = Column(Text)
    content = Column(Text)  # Yjs update data
    data = Column(JSON)
    meta = Column(JSON)

# API Keys
class APIKey(Base):
    __tablename__ = "apikey"
    id = Column(String, primary_key=True)
    api_key = Column(String, unique=True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(String)
    created_at = Column(Integer)
    is_active = Column(Boolean, default=True)

# Additional Models:
# - Group (user groups)
# - Tag (chat tags)
# - Folder (chat organization)
# - Memory (user memories for personalization)
# - Feedback (chat feedback)
# - Evaluation (model evaluations)
# - Tool (external tools)
# - Config (system configuration, persistent)
```

### 6.3 Database Migrations

**Tool:** Alembic
**Location:** `backend/open_webui/migrations/`

```bash
# Create new migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Automatic Migration on Startup:**
```python
# backend/open_webui/internal/db.py
def init_db():
    # Run Alembic migrations automatically
    run_migrations()
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
```

### 6.4 Database Optimization

**SQLite Optimizations:**
```python
# WAL mode for better concurrency
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  # 64MB cache
PRAGMA temp_store=MEMORY;
```

**PostgreSQL Optimizations:**
- Connection pooling (SQLAlchemy)
- pgvector extension for embeddings
- Indexes on frequently queried fields

---

## 7. RAG (Retrieval Augmented Generation) System

### 7.1 RAG Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                    RAG PIPELINE                            │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 1: DOCUMENT INGESTION                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Document Loaders (backend/retrieval/loaders/)        │  │
│  │  • PDF (pypdf)                                       │  │
│  │  • DOCX (python-docx)                               │  │
│  │  • PPTX (python-pptx)                               │  │
│  │  • Images + OCR (rapidocr)                          │  │
│  │  • Web pages (BeautifulSoup, Playwright)           │  │
│  │  • YouTube transcripts                              │  │
│  │  • Markdown, TXT, CSV                               │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 2: TEXT PROCESSING                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Text Splitters                                       │  │
│  │  • Recursive character splitter                     │  │
│  │  • Token-based splitter                             │  │
│  │  • Markdown header splitter                         │  │
│  │  • Configurable chunk size & overlap                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 3: EMBEDDING GENERATION                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Embedding Models                                     │  │
│  │  • Sentence-Transformers (local, default)           │  │
│  │  • OpenAI embeddings (external)                     │  │
│  │  • Hugging Face Transformers                        │  │
│  │  • Custom embedding endpoints                       │  │
│  │                                                      │  │
│  │ Config: RAG_EMBEDDING_MODEL                         │  │
│  │ Default: "sentence-transformers/all-MiniLM-L6-v2"   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 4: VECTOR STORAGE                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Vector Databases (10+ supported)                     │  │
│  │  • ChromaDB (default)                               │  │
│  │  • Qdrant                                           │  │
│  │  • Milvus                                           │  │
│  │  • Pinecone                                         │  │
│  │  • OpenSearch                                       │  │
│  │  • Elasticsearch                                    │  │
│  │  • PgVector (PostgreSQL)                           │  │
│  │  • S3Vector                                         │  │
│  │  • Oracle23ai                                       │  │
│  │                                                      │  │
│  │ Factory Pattern: backend/retrieval/vector/factory.py│  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 5: RETRIEVAL (Query Time)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Search Methods                                       │  │
│  │  • Semantic search (vector similarity)              │  │
│  │  • BM25 (keyword search)                            │  │
│  │  • Hybrid search (semantic + keyword)               │  │
│  │  • Configurable top-k results                       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 6: RERANKING (Optional)                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Reranking Models                                     │  │
│  │  • ColBERT                                          │  │
│  │  • Cross-encoders                                   │  │
│  │  • Custom reranking endpoints                       │  │
│  │                                                      │  │
│  │ Config: RAG_RERANKING_MODEL                         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  STEP 7: CONTEXT INJECTION                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Retrieved chunks injected into LLM prompt            │  │
│  │ Format: "Context: [chunk1]\n[chunk2]\n\nQuery: ..."  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
                      LLM Response
```

### 7.2 Vector Database Abstraction

**Factory Pattern:** `backend/retrieval/vector/factory.py`

```python
def get_vector_db(
    db_type: str,
    collection_name: str,
    embedding_function: Any
) -> VectorDBClient:
    """Factory to create vector DB client"""

    if db_type == "chroma":
        return ChromaClient(collection_name, embedding_function)
    elif db_type == "qdrant":
        return QdrantClient(collection_name, embedding_function)
    elif db_type == "milvus":
        return MilvusClient(collection_name, embedding_function)
    # ... and 7 more implementations

    raise ValueError(f"Unsupported vector DB: {db_type}")

# Abstract interface
class VectorDBClient(ABC):
    @abstractmethod
    def add_documents(self, documents: List[Document]):
        pass

    @abstractmethod
    def search(self, query: str, k: int = 5) -> List[Document]:
        pass

    @abstractmethod
    def delete_collection(self):
        pass
```

**Configuration:**
```python
VECTOR_DB = os.getenv("VECTOR_DB", "chroma")
CHROMA_CLIENT_AUTH_PROVIDER = os.getenv("CHROMA_CLIENT_AUTH_PROVIDER")
QDRANT_URL = os.getenv("QDRANT_URL")
MILVUS_URI = os.getenv("MILVUS_URI")
# ... specific configs for each DB
```

### 7.3 Web Search Integration

**Supported Providers (10+):**

```python
# backend/retrieval/web/searxng.py
def search_searxng(query: str, count: int = 5):
    """SearXNG meta-search engine"""

# backend/retrieval/web/google.py
def search_google(query: str, count: int = 5):
    """Google Programmable Search Engine"""

# backend/retrieval/web/brave.py
def search_brave(query: str, count: int = 5):
    """Brave Search API"""

# And 7 more providers:
# - DuckDuckGo
# - Bing
# - Tavily
# - Serper
# - Serpstack
# - SearchAPI
# - Firecrawl
```

**Web Search Flow:**
1. User query triggers web search
2. Provider API called (e.g., Brave)
3. Results fetched (title, snippet, URL)
4. Web page content extracted
5. Content chunked and embedded
6. Injected into RAG context

### 7.4 Knowledge Base Integration

**UI Usage:** Users can reference knowledge with `#` syntax:
```
User: Tell me about our product #product-docs
```

**Backend Flow:**
1. Parse `#product-docs` reference
2. Look up Knowledge by ID/name
3. Retrieve associated file IDs
4. Query vector DB for relevant chunks
5. Inject into LLM context

**Access Control:**
```python
class Knowledge:
    access_control = {
        "read": {
            "user_ids": ["user1", "user2"],
            "group_ids": ["group1"]
        },
        "write": {
            "user_ids": ["admin1"]
        }
    }
```

---

## 8. Real-Time Communication

### 8.1 Socket.IO Architecture

**Location:** `backend/socket/main.py`

```python
import socketio
from socketio import AsyncServer

# Create Socket.IO server
sio = AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Session manager (Redis or in-memory)
if REDIS_URL:
    mgr = socketio.AsyncRedisManager(REDIS_URL)
    sio = AsyncServer(client_manager=mgr, ...)
else:
    # In-memory (single instance only)
    mgr = socketio.AsyncManager()

# Authentication
@sio.event
async def connect(sid, environ, auth):
    token = auth.get('token')
    user = verify_jwt(token)
    if not user:
        raise ConnectionRefusedError('Invalid token')

    await sio.save_session(sid, {'user_id': user.id})

# Event handlers
@sio.event
async def message(sid, data):
    """Handle incoming message"""
    session = await sio.get_session(sid)
    user_id = session['user_id']

    # Process message
    # Broadcast to room
    await sio.emit('message', data, room=data['chat_id'])

@sio.event
async def join_chat(sid, chat_id):
    """Join chat room"""
    await sio.enter_room(sid, chat_id)
    await sio.emit('user_join', {'sid': sid}, room=chat_id)

@sio.event
async def leave_chat(sid, chat_id):
    """Leave chat room"""
    await sio.leave_room(sid, chat_id)
    await sio.emit('user_leave', {'sid': sid}, room=chat_id)
```

### 8.2 Yjs Collaboration (Notes)

**CRDT for Conflict-Free Editing:**

```python
# backend/socket/utils.py
from y_py import YDoc
import y_py as Y

class YdocManager:
    """Manage Yjs documents for collaborative editing"""

    def __init__(self):
        self.docs = {}  # note_id -> YDoc

    def get_or_create(self, note_id: str) -> YDoc:
        if note_id not in self.docs:
            self.docs[note_id] = YDoc()
        return self.docs[note_id]

    def apply_update(self, note_id: str, update: bytes):
        """Apply Yjs update from client"""
        ydoc = self.get_or_create(note_id)
        Y.apply_update(ydoc, update)

    def get_state_vector(self, note_id: str) -> bytes:
        """Get current state for sync"""
        ydoc = self.get_or_create(note_id)
        return Y.encode_state_vector(ydoc)
```

**Client-Server Sync:**
```
Client 1 types → Yjs update → WebSocket → Server → Broadcast
                                                    ↓
Client 2, 3, ... ← WebSocket ← Yjs update ← Apply to YDoc
```

**Benefits:**
- Automatic conflict resolution
- Offline-first (sync when reconnected)
- No OT (Operational Transformation) complexity
- Built-in undo/redo

### 8.3 Streaming Responses

**Server-Sent Events (SSE) for LLM Streaming:**

```python
from fastapi.responses import StreamingResponse

@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    async def event_stream():
        async for chunk in llm_stream(request.messages):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
```

**Client (Frontend):**
```typescript
const eventSource = new EventSource('/api/chat/completions');
eventSource.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  // Append to message
};
```

---

## 9. Authentication & Authorization

### 9.1 Authentication Methods

```
┌─────────────────────────────────────────────────────────┐
│              AUTHENTICATION METHODS                     │
└─────────────────────────────────────────────────────────┘
                          ↓
    ┌───────────┬───────────┬──────────┬─────────┬────────┐
    ↓           ↓           ↓          ↓         ↓        ↓
  Local      OAuth2      LDAP       SCIM     API Keys  Trusted
  Auth                                                  Headers
    │           │           │          │         │        │
    └───────────┴───────────┴──────────┴─────────┴────────┘
                          ↓
                  JWT Token Issued
                          ↓
              Stored in localStorage/cookie
                          ↓
          Included in Authorization header
                          ↓
              Validated on each request
```

#### 9.1.1 Local Authentication

**Password Hashing:** bcrypt with salt rounds = 12

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**Signup Flow:**
```python
@router.post("/signup")
async def signup(form: SignupForm):
    # Check if email exists
    if Users.get_user_by_email(form.email):
        raise HTTPException(400, "Email already exists")

    # Hash password
    hashed = hash_password(form.password)

    # Create user
    user = Users.insert_new_user(
        id=str(uuid.uuid4()),
        name=form.name,
        email=form.email,
        password=hashed,
        role="pending" if ENABLE_SIGNUP_APPROVAL else "user"
    )

    # Generate JWT
    token = create_token(user.id)

    return {"token": token, "user": user}
```

#### 9.1.2 OAuth2 Integration

**Supported Providers:**
- Google
- GitHub
- Microsoft Azure AD
- Okta
- Auth0
- Custom OIDC providers

**OAuth Flow:**
```python
@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(provider: str):
    # Redirect to OAuth provider
    auth_url = get_oauth_url(provider)
    return RedirectResponse(auth_url)

@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str):
    # Exchange code for access token
    token = exchange_code(provider, code)

    # Get user info
    user_info = get_user_info(provider, token)

    # Create or update user
    user = Users.get_user_by_oauth_sub(user_info['sub'])
    if not user:
        user = Users.insert_new_user(
            id=str(uuid.uuid4()),
            name=user_info['name'],
            email=user_info['email'],
            oauth_sub=user_info['sub'],
            role="user"
        )

    # Generate JWT
    jwt = create_token(user.id)
    return {"token": jwt, "user": user}
```

#### 9.1.3 LDAP/Active Directory

```python
from ldap3 import Server, Connection

def authenticate_ldap(username: str, password: str):
    server = Server(LDAP_SERVER_URL)

    # Bind DN template
    user_dn = f"uid={username},{LDAP_BASE_DN}"

    conn = Connection(server, user_dn, password)
    if not conn.bind():
        raise AuthenticationError("Invalid credentials")

    # Get user attributes
    conn.search(LDAP_BASE_DN, f"(uid={username})", attributes=['*'])
    user_info = conn.entries[0]

    return {
        'username': username,
        'email': user_info.mail.value,
        'name': user_info.displayName.value
    }
```

#### 9.1.4 SCIM 2.0 (Enterprise)

**Automated User Provisioning:**

```python
# backend/routers/scim.py

@router.post("/scim/v2/Users")
async def create_scim_user(user: SCIMUser):
    """Create user via SCIM"""
    new_user = Users.insert_new_user(
        id=user.externalId or str(uuid.uuid4()),
        name=user.displayName,
        email=user.emails[0].value,
        role="user"
    )
    return SCIMUserResponse.from_user(new_user)

@router.patch("/scim/v2/Users/{user_id}")
async def update_scim_user(user_id: str, operations: List[SCIMOperation]):
    """Update user via SCIM PATCH"""
    user = Users.get_user_by_id(user_id)
    for op in operations:
        if op.op == "replace":
            setattr(user, op.path, op.value)
    Users.update_user(user)
    return SCIMUserResponse.from_user(user)
```

**Integration:** Okta, Azure AD, Google Workspace

### 9.2 JWT Token Structure

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("WEBUI_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> str:
    """Returns user_id or raises exception"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

### 9.3 Authorization (RBAC)

**Role-Based Access Control:**

```python
class Role:
    ADMIN = "admin"
    USER = "user"
    PENDING = "pending"

def get_current_user(token: str = Depends(oauth2_scheme)):
    user_id = verify_token(token)
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user

def get_admin_user(user: Users = Depends(get_current_user)):
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Admin access required")
    return user

# Usage:
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: Users = Depends(get_admin_user)  # Admin-only
):
    Users.delete_user(user_id)
    return {"success": True}
```

**Fine-Grained Access Control (Knowledge):**

```python
def check_knowledge_access(
    knowledge: Knowledge,
    user: Users,
    permission: str = "read"
) -> bool:
    """Check if user has permission to knowledge"""

    ac = knowledge.access_control
    if not ac:
        return knowledge.user_id == user.id  # Owner only

    perms = ac.get(permission, {})

    # Check user ID
    if user.id in perms.get("user_ids", []):
        return True

    # Check group membership
    user_groups = Groups.get_groups_by_user_id(user.id)
    for group in user_groups:
        if group.id in perms.get("group_ids", []):
            return True

    # Check if owner
    if user.id == knowledge.user_id:
        return True

    return False
```

---

## 10. Plugin & Extension System

### 10.1 Pipelines Framework

**Architecture:** HTTP-based middleware pattern

```
Client Request → Open WebUI → Pipeline Filter → LLM → Pipeline Outlet → Response
```

**Pipeline Types:**
1. **Filter**: Pre-process requests before LLM
2. **Model**: Replace/wrap LLM
3. **Outlet**: Post-process LLM responses

**Registration:**

```python
# backend/routers/pipelines.py

# Pipelines are external services
# Open WebUI calls them via HTTP

PIPELINES_URL = os.getenv("PIPELINES_URL", "http://localhost:9099")

async def call_pipeline(pipeline_id: str, data: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{PIPELINES_URL}/filter",
            json={"pipeline_id": pipeline_id, **data}
        ) as resp:
            return await resp.json()
```

**Example Pipeline (External Service):**

```python
# External pipeline service (FastAPI)
from fastapi import FastAPI

app = FastAPI()

@app.post("/filter")
async def filter_inlet(data: dict):
    """Pre-process request"""
    messages = data["messages"]

    # Example: Rate limiting
    if check_rate_limit(data["user_id"]):
        raise HTTPException(429, "Rate limit exceeded")

    # Example: Toxicity filter
    for msg in messages:
        if is_toxic(msg["content"]):
            msg["content"] = "[FILTERED]"

    return {"messages": messages}

@app.post("/outlet")
async def filter_outlet(data: dict):
    """Post-process response"""
    response = data["response"]

    # Example: Translation
    translated = translate(response, target_lang="es")

    return {"response": translated}
```

**Benefits:**
- Language-agnostic (HTTP-based)
- Scalable (separate service)
- Composable (chain multiple pipelines)
- Custom logic (rate limit, translation, monitoring, etc.)

### 10.2 Custom Functions (Python)

**Native Python Function Calling:**

```python
# User writes function in Web UI code editor
def get_weather(location: str) -> dict:
    """Get current weather for a location"""
    import requests
    api_key = "YOUR_KEY"
    resp = requests.get(
        f"https://api.weather.com/{location}?key={api_key}"
    )
    return resp.json()
```

**Execution:**

```python
# backend/utils/plugin.py
from RestrictedPython import compile_restricted, safe_globals

def execute_function(code: str, function_name: str, args: dict):
    """Safely execute user-provided Python function"""

    # Compile with RestrictedPython (sandbox)
    byte_code = compile_restricted(
        code,
        filename='<user_function>',
        mode='exec'
    )

    # Execute in restricted globals
    exec_globals = safe_globals.copy()
    exec(byte_code, exec_globals)

    # Call function
    func = exec_globals[function_name]
    result = func(**args)

    return result
```

**LLM Integration:**

```python
# LLM can call functions via function calling API
{
  "model": "gpt-4",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          }
        }
      }
    }
  ]
}
```

**Security:**
- RestrictedPython sandbox (no file I/O, no imports by default)
- Timeout limits
- Resource limits (memory, CPU)
- Admin approval for global functions

### 10.3 MCP (Model Context Protocol) Integration

**Status:** Scaffolded in `backend/utils/mcp/client.py`

**Purpose:** Standard interface for AI context sharing

**Potential Integration:**

```python
# backend/utils/mcp/client.py
class MCPClient:
    """Model Context Protocol client"""

    def get_context(self, resource_uri: str) -> dict:
        """Fetch context from MCP server"""
        # Implementation for MCP protocol
        pass

    def call_tool(self, tool_name: str, params: dict) -> dict:
        """Call MCP tool"""
        # Implementation
        pass

# Usage in chat:
mcp_client = MCPClient(MCP_SERVER_URL)
context = mcp_client.get_context("file:///project/README.md")
# Inject context into LLM
```

---

## 11. AI/ML Integration Layer

### 11.1 Multi-LLM Support

**Supported Backends:**

```
1. Ollama (Local)
   - Endpoint: http://localhost:11434
   - Models: Pull from Ollama library

2. OpenAI-Compatible APIs
   - OpenAI GPT-4, GPT-3.5
   - Anthropic Claude
   - Google Gemini
   - Groq
   - Mistral
   - Together AI
   - Perplexity
   - OpenRouter (aggregator)
   - LM Studio (local)

3. Custom Endpoints
   - Any OpenAI-compatible API
   - Configure via OPENAI_API_BASE_URL
```

**Configuration:**

```python
# backend/config.py

OLLAMA_BASE_URLS = os.getenv("OLLAMA_BASE_URLS", "http://localhost:11434")
OPENAI_API_BASE_URLS = os.getenv("OPENAI_API_BASE_URLS", "https://api.openai.com/v1")
OPENAI_API_KEYS = os.getenv("OPENAI_API_KEYS", "")

# Multiple endpoints support
OLLAMA_BASE_URLS = [
    "http://ollama1:11434",
    "http://ollama2:11434"
]
```

### 11.2 Model Management

**Model Pulling (Ollama):**

```python
@router.post("/models/pull")
async def pull_model(form: PullModelForm):
    """Pull Ollama model"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": form.name}
        ) as resp:
            async for line in resp.content:
                yield line  # Stream progress
```

**Model Builder:**

```python
@router.post("/models/create")
async def create_model(form: CreateModelForm):
    """Create custom Ollama model via Modelfile"""

    modelfile = f"""
    FROM {form.base_model}
    SYSTEM {form.system_prompt}
    PARAMETER temperature {form.temperature}
    """

    # Create via Ollama API
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"{OLLAMA_BASE_URL}/api/create",
            json={"name": form.name, "modelfile": modelfile}
        )
```

### 11.3 Inference Flow

```python
# Unified interface for all LLM backends

async def generate_completion(
    model: str,
    messages: List[dict],
    stream: bool = False
):
    # Determine backend (Ollama vs OpenAI-compatible)
    if is_ollama_model(model):
        return await ollama_generate(model, messages, stream)
    else:
        return await openai_generate(model, messages, stream)

async def ollama_generate(model, messages, stream):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": stream}
        ) as resp:
            if stream:
                async for line in resp.content:
                    yield json.loads(line)
            else:
                return await resp.json()

async def openai_generate(model, messages, stream):
    import openai
    client = openai.AsyncOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE_URL
    )

    if stream:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        async for chunk in stream:
            yield chunk
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response
```

### 11.4 Function Calling Integration

**OpenAI-Style Function Calling:**

```python
# Chat request with tools
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "What's the weather in SF?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }
  ]
}

# LLM response with function call
{
  "choices": [{
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "id": "call_123",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"location\": \"San Francisco\"}"
        }
      }]
    }
  }]
}

# Execute function
result = execute_function("get_weather", {"location": "San Francisco"})

# Send result back to LLM
{
  "role": "tool",
  "tool_call_id": "call_123",
  "content": json.dumps(result)
}
```

### 11.5 Image Generation

**Supported Backends:**

```python
IMAGE_GENERATION_ENGINE = os.getenv("IMAGE_GENERATION_ENGINE", "")

# Options:
# - "openai" → DALL-E 3
# - "comfyui" → ComfyUI (local)
# - "automatic1111" → Stable Diffusion WebUI (local)
```

**Image Generation Flow:**

```python
@router.post("/images/generate")
async def generate_image(form: ImageGenerationForm):
    if IMAGE_GENERATION_ENGINE == "openai":
        return await generate_dalle(form.prompt)
    elif IMAGE_GENERATION_ENGINE == "comfyui":
        return await generate_comfyui(form.prompt)
    elif IMAGE_GENERATION_ENGINE == "automatic1111":
        return await generate_sd_webui(form.prompt)
```

---

## 12. Storage Architecture

### 12.1 Storage Provider Abstraction

**Supported Backends:**

```python
STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "local")

# Options:
# - "local"  → Local filesystem
# - "s3"     → AWS S3
# - "azure"  → Azure Blob Storage
# - "gcs"    → Google Cloud Storage
```

### 12.2 Storage Interface

```python
# backend/storage/provider.py

class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file_path: str, content: bytes) -> str:
        """Upload file, return URL"""
        pass

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """Download file content"""
        pass

    @abstractmethod
    async def delete(self, file_path: str):
        """Delete file"""
        pass

    @abstractmethod
    async def list(self, prefix: str) -> List[str]:
        """List files with prefix"""
        pass

# Factory
def get_storage_provider() -> StorageProvider:
    if STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    elif STORAGE_PROVIDER == "s3":
        return S3StorageProvider()
    elif STORAGE_PROVIDER == "azure":
        return AzureStorageProvider()
    elif STORAGE_PROVIDER == "gcs":
        return GCSStorageProvider()
```

### 12.3 S3 Implementation

```python
import boto3
from botocore.client import Config

class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
            config=Config(signature_version='s3v4')
        )
        self.bucket = S3_BUCKET_NAME

    async def upload(self, file_path: str, content: bytes) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=file_path,
            Body=content
        )
        return f"s3://{self.bucket}/{file_path}"

    async def download(self, file_path: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=file_path)
        return obj['Body'].read()
```

---

## 13. Deployment Architecture

### 13.1 Docker Deployment

**Single Container:**

```dockerfile
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install -e .

# Copy built frontend
COPY --from=frontend-builder /app/build /app/static

# Expose port
EXPOSE 8080

# Run server
CMD ["python", "-m", "open_webui", "serve"]
```

**Docker Compose:**

```yaml
version: '3.8'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - DATABASE_URL=postgresql://user:pass@db:5432/webui
      - REDIS_URL=redis://redis:6379
      - STORAGE_PROVIDER=s3
    volumes:
      - open-webui-data:/app/backend/data
    depends_on:
      - ollama
      - db
      - redis

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=webui
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pg-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  open-webui-data:
  ollama-data:
  pg-data:
  redis-data:
```

### 13.2 Kubernetes Deployment

**Helm Chart Structure:**

```
kubernetes/helm/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secret.yaml
    └── pvc.yaml
```

**Key Kubernetes Resources:**

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: open-webui
spec:
  replicas: 3
  selector:
    matchLabels:
      app: open-webui
  template:
    metadata:
      labels:
        app: open-webui
    spec:
      containers:
      - name: open-webui
        image: ghcr.io/open-webui/open-webui:main
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: open-webui-secret
              key: database-url
        - name: REDIS_URL
          value: redis://open-webui-redis:6379
        volumeMounts:
        - name: data
          mountPath: /app/backend/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: open-webui-pvc
```

### 13.3 Scaling Considerations

**Horizontal Scaling:**
- Multiple Open WebUI instances behind load balancer
- Redis-backed Socket.IO for session sharing
- PostgreSQL for database (better concurrency than SQLite)
- External object storage (S3/Azure/GCS) for files
- Distributed vector DB (Qdrant, Milvus cluster)

**Vertical Scaling:**
- Increase CPU/memory for embedding generation
- GPU for local LLM inference (Ollama)
- More database connections

---

## 14. Security Architecture

### 14.1 Security Layers

```
┌────────────────────────────────────────────────────────┐
│  1. Network Security                                   │
│  - HTTPS/TLS encryption                               │
│  - CORS policies                                      │
│  - Rate limiting                                      │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│  2. Authentication                                     │
│  - JWT tokens (HS256)                                 │
│  - OAuth2/OIDC                                        │
│  - LDAP/AD                                            │
│  - SCIM 2.0                                           │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│  3. Authorization (RBAC)                               │
│  - Role-based access (admin/user/pending)             │
│  - Fine-grained permissions (knowledge, models)       │
│  - API key scoping                                    │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│  4. Data Security                                      │
│  - Password hashing (bcrypt)                          │
│  - Secret management (env vars)                       │
│  - Database encryption at rest (provider-dependent)   │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│  5. Code Execution Security                            │
│  - RestrictedPython sandbox                           │
│  - Resource limits (timeout, memory)                  │
│  - Admin approval for global functions                │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│  6. Content Security                                   │
│  - XSS prevention (DOMPurify)                         │
│  - CSRF protection                                    │
│  - Input validation (Pydantic)                        │
└────────────────────────────────────────────────────────┘
```

### 14.2 Audit Logging

```python
# backend/utils/middleware.py

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Log all API requests for audit"""

    user_id = None
    if request.headers.get("Authorization"):
        try:
            user_id = verify_token(request.headers["Authorization"])
        except:
            pass

    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "method": request.method,
        "path": request.url.path,
        "user_id": user_id,
        "ip": request.client.host,
        "user_agent": request.headers.get("User-Agent")
    }

    logger.info(f"API Request: {json.dumps(log_data)}")

    response = await call_next(request)

    log_data["status_code"] = response.status_code
    logger.info(f"API Response: {json.dumps(log_data)}")

    return response
```

---

## 15. Scalability & Performance

### 15.1 Performance Optimizations

**Frontend:**
- Code splitting (Vite)
- Lazy loading routes
- Virtual scrolling for long lists
- Debounced search inputs
- Cached API responses

**Backend:**
- Async I/O (FastAPI + aiohttp)
- Database connection pooling
- Redis caching
- Compression middleware (gzip)
- Pagination for large datasets

**Database:**
- Indexes on frequently queried columns
- Query optimization
- Connection pooling
- Read replicas (PostgreSQL)

**RAG:**
- Batch embedding generation
- Vector DB query optimization
- Caching embedding results
- Async document processing

### 15.2 Monitoring

**Metrics to Track:**
- Request latency (p50, p95, p99)
- Error rates
- Active users (Socket.IO)
- Database query performance
- LLM response times
- Vector DB query times
- Storage usage

**Logging:**
```python
from loguru import logger

logger.add(
    "logs/webui_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    format="{time} | {level} | {message}"
)
```

---

## 16. Integration Points

### 16.1 Current Integrations

- **Ollama**: Local LLM inference
- **OpenAI**: GPT models
- **Anthropic**: Claude models
- **Google**: Gemini models
- **Web Search**: 10+ providers
- **OAuth**: Multiple IdPs
- **LDAP**: Active Directory
- **SCIM**: Enterprise provisioning
- **Vector DBs**: 10+ options
- **Storage**: S3, Azure, GCP
- **Image Generation**: DALL-E, ComfyUI, SD WebUI
- **Speech**: Whisper (STT), Kokoro (TTS)

### 16.2 Extension Points for Future Integrations

1. **MCP UI (Model Context Protocol)**
   - Entry point: `backend/utils/mcp/client.py`
   - Integration: Tool/function calling

2. **AG-UI (Agentic UI)**
   - Entry point: Custom pipeline or tool
   - Real-time: Socket.IO events

3. **Bolt.diy**
   - Entry point: Custom function or pipeline
   - UI: Embedded iframe or API calls

4. **Flowise**
   - Entry point: OpenAI-compatible API wrapper
   - Integration: External tool endpoint

5. **screenshot-to-code**
   - Entry point: Image file upload + function
   - Vision: MediaPipe or external API
   - Output: Code injection into chat

**Integration Pattern:**
```
External Service → Pipeline/Tool → Open WebUI → LLM Context
```

---

## Appendix

### A. Key Files Reference

| File | LOC | Purpose |
|------|-----|---------|
| `backend/open_webui/main.py` | 500 | FastAPI app entry point |
| `backend/open_webui/config.py` | 3000+ | Configuration management |
| `backend/open_webui/socket/main.py` | 800 | Socket.IO server |
| `backend/open_webui/retrieval/utils.py` | 1500 | RAG core functions |
| `src/lib/stores/index.ts` | 400 | Global state stores |
| `src/routes/+layout.svelte` | 600 | App initialization |

### B. Environment Variables

See `backend/open_webui/config.py` for 150+ configurable environment variables.

### C. API Versioning

Current API version: **v1** (no versioning in URLs yet)

Future: `/api/v2/...` for breaking changes

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-05 | Open WebUI Team | Initial comprehensive architecture documentation |

---

**For questions or contributions, please visit:**
- GitHub: https://github.com/open-webui/open-webui
- Documentation: https://docs.openwebui.com
- Discord: https://discord.gg/5rJgQTnV4s
