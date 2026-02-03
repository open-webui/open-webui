# Architecture Overview

> **Purpose:** High-level system design and component relationships
> **Audience:** Developers understanding the codebase structure
> **Usage:** Reference when planning features or debugging cross-cutting issues

---

## Prerequisites

- `PRODUCT_OVERVIEW.md` — Feature understanding

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENTS                                        │
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Browser    │  │  Mobile App  │  │  API Client  │  │   Webhook    │        │
│  │  (SvelteKit) │  │   (Future)   │  │  (External)  │  │  (External)  │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
└─────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │                  │
          │         REST API │ + SSE + WebSocket│                  │
          │                  │                  │                  │
┌─────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┐
│         ▼                  ▼                  ▼                  ▼              │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                           FASTAPI APPLICATION                             │  │
│  │                                                                           │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                           MIDDLEWARE                                 │ │  │
│  │  │  • Authentication (JWT validation)                                   │ │  │
│  │  │  • CORS handling                                                     │ │  │
│  │  │  • Request/Response transformation                                   │ │  │
│  │  │  • Rate limiting                                                     │ │  │
│  │  └─────────────────────────────────────────────────────────────────────┘ │  │
│  │                                    │                                      │  │
│  │  ┌─────────────────────────────────┼─────────────────────────────────┐   │  │
│  │  │                          ROUTERS (25+)                             │   │  │
│  │  │                                                                     │   │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │  │
│  │  │  │  auths   │ │  chats   │ │  openai  │ │retrieval │ │ channels │ │   │  │
│  │  │  │  users   │ │ messages │ │  ollama  │ │knowledge │ │  notes   │ │   │  │
│  │  │  │  groups  │ │ folders  │ │  models  │ │  files   │ │ memories │ │   │  │
│  │  │  │  ...     │ │  ...     │ │  ...     │ │  ...     │ │  ...     │ │   │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │   │  │
│  │  └─────────────────────────────────┼─────────────────────────────────┘   │  │
│  │                                    │                                      │  │
│  │  ┌─────────────────────────────────┼─────────────────────────────────┐   │  │
│  │  │                           SERVICES                                 │   │  │
│  │  │                                                                     │   │  │
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐   │   │  │
│  │  │  │   Socket.IO  │ │  Retrieval   │ │      LLM Providers       │   │   │  │
│  │  │  │  (Real-time) │ │    (RAG)     │ │ OpenAI/Ollama/Anthropic  │   │   │  │
│  │  │  └──────────────┘ └──────────────┘ └──────────────────────────┘   │   │  │
│  │  └───────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                         │
│  ┌────────────────────────────────────┼────────────────────────────────────┐   │
│  │                              DATA LAYER                                  │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │  SQLAlchemy  │  │  Vector DB   │  │    Redis     │  │   Storage  │  │   │
│  │  │   (ORM)      │  │  (ChromaDB)  │  │  (Optional)  │  │   (Files)  │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬─────┘  │   │
│  │         │                 │                 │                 │         │   │
│  │         ▼                 ▼                 ▼                 ▼         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │SQLite/PG/MySQL│ │ChromaDB/etc │  │ Redis Server │  │Local/S3    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Hierarchy

### Frontend (SvelteKit)

```
src/
├── routes/                      # File-based routing
│   ├── +layout.svelte          # Root layout (auth, init)
│   ├── +page.svelte            # Home redirect
│   ├── auth/                   # Authentication pages
│   │   └── +page.svelte        # Login/signup
│   └── (app)/                  # Protected routes group
│       ├── +layout.svelte      # App shell (sidebar, header)
│       ├── +page.svelte        # Main chat interface
│       ├── c/[id]/             # Chat by ID
│       ├── admin/              # Admin panel
│       ├── channels/           # Channel messaging
│       ├── playground/         # AI playgrounds
│       └── workspace/          # Collaborative tools
│
├── lib/
│   ├── apis/                   # Backend API clients
│   │   ├── index.ts           # Main chat API
│   │   ├── auths/             # Auth endpoints
│   │   ├── chats/             # Chat CRUD
│   │   ├── models/            # Model listing
│   │   └── ...                # 26 API modules
│   │
│   ├── components/            # Reusable components
│   │   ├── chat/              # Chat interface
│   │   ├── admin/             # Admin UI
│   │   ├── common/            # Shared UI elements
│   │   └── ...
│   │
│   ├── stores/                # Svelte stores
│   │   └── index.ts           # All application state
│   │
│   └── utils/                 # Utilities
│       ├── formatting.ts
│       └── ...
```

### Backend (FastAPI)

```
backend/open_webui/
├── main.py                     # Application entry, router registration
├── config.py                   # Runtime configuration
├── env.py                      # Environment variable loading
│
├── routers/                    # API endpoint modules
│   ├── auths.py               # Authentication (1200+ lines)
│   ├── chats.py               # Chat CRUD
│   ├── openai.py              # OpenAI proxy (1000+ lines)
│   ├── ollama.py              # Ollama integration
│   ├── retrieval.py           # RAG endpoints (3000+ lines)
│   ├── channels.py            # Real-time channels
│   ├── analytics.py           # Usage analytics
│   └── ...                    # 25+ router modules
│
├── models/                     # SQLAlchemy ORM models
│   ├── users.py               # User entity
│   ├── chats.py               # Chat entity
│   ├── chat_messages.py       # Message analytics
│   ├── channels.py            # Channel entities
│   └── ...                    # 20 model files
│
├── socket/                     # WebSocket handling
│   ├── main.py                # Socket.IO server
│   └── utils.py               # Redis utilities
│
├── retrieval/                  # RAG pipeline
│   ├── loaders/               # Document loaders
│   ├── vector/                # Vector DB clients
│   └── utils.py               # Embedding utilities
│
├── storage/                    # File storage
│   └── provider.py            # Local/S3 abstraction
│
├── utils/                      # Utilities
│   ├── auth.py                # JWT, dependencies
│   ├── middleware.py          # Request transformation
│   ├── access_control.py      # Permission checking
│   └── ...
│
├── internal/                   # Internal modules
│   └── db.py                  # Database setup
│
└── migrations/                 # Alembic migrations
    └── versions/              # 60+ migration files
```

---

## Key Design Patterns

### 1. Provider Abstraction

LLM providers are abstracted behind a common interface:

```
Frontend                 Backend                   Providers
   │                        │                          │
   │  POST /chat/          │                          │
   │  completions          │                          │
   │ ─────────────────────▶│                          │
   │                        │  ┌──────────────────┐   │
   │                        │  │    Middleware    │   │
   │                        │  │ • System prompt  │   │
   │                        │  │ • RAG injection  │   │
   │                        │  │ • Model params   │   │
   │                        │  └────────┬─────────┘   │
   │                        │           │             │
   │                        │     Route to provider   │
   │                        │           │             │
   │                        │  ┌────────┼────────┐    │
   │                        │  ▼        ▼        ▼    │
   │                        │ OpenAI  Ollama  Anthropic
   │                        │  │        │        │    │
   │  ◀──── SSE Stream ─────┼──┴────────┴────────┘    │
   │                        │                          │
```

### 2. Dependency Injection

FastAPI dependencies handle cross-cutting concerns:

```python
# Authentication chain
@router.get("/endpoint")
async def endpoint(
    user: UserModel = Depends(get_verified_user),  # Auth required
    db: Session = Depends(get_session),            # DB session
):
    pass

# Dependency hierarchy
get_current_user      # Extract user from token (optional)
    ↓
get_verified_user     # Require valid user (401 if not)
    ↓
get_admin_user        # Require admin role (403 if not)
```

### 3. Real-Time Communication

Socket.IO handles bidirectional communication:

```
┌─────────────┐                    ┌─────────────┐
│   Client    │                    │   Server    │
│  (Browser)  │                    │ (Socket.IO) │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       │ connect (auth: {token})          │
       │─────────────────────────────────▶│
       │                                  │ Validate token
       │                                  │ Join user room
       │◀─────────────────────────────────│
       │ connected                        │
       │                                  │
       │ emit("usage", {model: "gpt-4"})  │
       │─────────────────────────────────▶│
       │                                  │ Track usage
       │                                  │
       │◀─────────────────────────────────│
       │ on("model:status", data)         │ Broadcast updates
       │                                  │
```

### 4. Access Control

Flexible permission model for resources:

```python
# Access control structure
access_control = {
    "read": {
        "group_ids": ["group-1", "group-2"],
        "user_ids": ["user-1"]
    },
    "write": {
        "group_ids": ["group-1"],
        "user_ids": []
    }
}

# Evaluation
def has_access(user: User, resource, permission: str) -> bool:
    if user.role == "admin":
        return True  # Admin bypass

    acl = resource.access_control.get(permission, {})

    # Check user ID
    if user.id in acl.get("user_ids", []):
        return True

    # Check group membership
    user_groups = get_user_groups(user.id)
    if any(g.id in acl.get("group_ids", []) for g in user_groups):
        return True

    return False
```

---

## Data Flow Patterns

### Chat Message Flow

```
1. User sends message
   ↓
2. Frontend calls POST /api/chat/completions
   ↓
3. Middleware processes request:
   • Injects system prompt
   • Retrieves RAG context (if knowledge base selected)
   • Applies model parameters
   ↓
4. Request forwarded to LLM provider
   ↓
5. Streaming response via SSE
   ↓
6. Frontend renders tokens as they arrive
   ↓
7. On completion:
   • Save to Chat.chat JSON
   • Write to chat_messages table (analytics)
   • Update usage tracking
```

### RAG Retrieval Flow

```
1. User selects knowledge base
   ↓
2. User sends query
   ↓
3. Query embedded using sentence-transformer
   ↓
4. Similarity search in vector DB
   ↓
5. Top-k chunks retrieved
   ↓
6. Chunks injected into system prompt
   ↓
7. LLM generates response with context
```

---

## Configuration Layers

```
┌─────────────────────────────────────────────────────────┐
│                   Environment Variables                  │
│           (.env file or container environment)           │
│                                                         │
│  DATABASE_URL, WEBUI_SECRET_KEY, OPENAI_API_KEY, etc.  │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                        env.py                            │
│              (Parse and validate env vars)               │
│                                                         │
│  Loads from os.environ, applies defaults, type coercion │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                       config.py                          │
│                (Runtime configuration)                   │
│                                                         │
│  Values that can change at runtime, stored in app.state │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     app.state.config                     │
│               (Live application config)                  │
│                                                         │
│  Modifiable via admin API, persists in memory/database  │
└─────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Single Instance

```
┌─────────────────────────────────────────────┐
│              Docker Container               │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         Open WebUI (Uvicorn)         │   │
│  │                                       │   │
│  │  • FastAPI backend                    │   │
│  │  • SvelteKit static build             │   │
│  │  • Socket.IO (in-process)             │   │
│  └───────────────────┬───────────────────┘   │
│                      │                       │
│  ┌──────────┐  ┌─────┴─────┐  ┌───────────┐ │
│  │  SQLite  │  │  ChromaDB │  │   Files   │ │
│  └──────────┘  └───────────┘  └───────────┘ │
└─────────────────────────────────────────────┘
```

### Multi-Instance (Production)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Load Balancer                                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   Instance 1  │       │   Instance 2  │       │   Instance 3  │
│   Open WebUI  │       │   Open WebUI  │       │   Open WebUI  │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  PostgreSQL   │       │     Redis     │       │    Qdrant     │
│  (Database)   │       │ (Sessions/WS) │       │  (Vector DB)  │
└───────────────┘       └───────────────┘       └───────────────┘
```

---

## Related Documents

- `SYSTEM_TOPOLOGY.md` — Runtime data flows
- `TESTING_STRATEGY.md` — Test architecture
- ADRs — Design decision rationale

---

*Last updated: 2026-02-03*
