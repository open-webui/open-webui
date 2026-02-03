# Open WebUI

> A self-hosted, feature-rich, extensible AI chat interface supporting multiple LLM providers with RAG capabilities, real-time collaboration, and enterprise authentication.

---

## Part I: Features

### Core Chat Experience
- **Multi-Model Conversations** — Chat with OpenAI, Ollama, Anthropic, Google Gemini, Azure OpenAI, and any OpenAI-compatible endpoint
- **Streaming Responses** — Real-time token streaming with Server-Sent Events (SSE)
- **Chat Management** — Organize conversations with folders, tags, pinning, and archiving
- **Chat Sharing** — Generate public links to share conversations; manage and revoke shared links
- **Chat Export/Import** — Export conversations as JSON; import from other platforms

### Retrieval-Augmented Generation (RAG)
- **Knowledge Bases** — Create collections of documents for context injection
- **Document Processing** — Support for PDF, DOCX, PPTX, TXT, MD, and 15+ file types
- **Vector Search** — ChromaDB (default), Qdrant, Pinecone, Weaviate, Milvus, OpenSearch
- **Hybrid Search** — Combines semantic embeddings with BM25 keyword matching
- **Web Search Integration** — DuckDuckGo, Google, Brave, Tavily, Serper, and more
- **Web Scraping** — Firecrawl integration for extracting web content

### Real-Time Collaboration
- **Channels** — Group chat, direct messages, and announcement channels
- **Message Reactions** — Emoji reactions on channel messages
- **Webhooks** — Incoming webhooks for bot/integration message posting
- **Collaborative Notes** — Real-time collaborative editing with YCRDT
- **User Presence** — Online/away status with custom status messages

### AI Playgrounds
- **Chat Playground** — Test models with different parameters
- **Image Generation** — Generate images with supported providers
- **Model Comparison** — Side-by-side model response comparison

### Tools & Functions
- **Custom Tools** — Define tools via OpenAPI specifications for model function calling
- **Custom Functions** — Server-side Python functions (filters, actions) with RestrictedPython sandbox
- **MCP Integration** — Model Context Protocol tool server support
- **Tool Servers** — Connect to external OpenAPI-based tool servers

### Enterprise Features
- **Multi-Auth Support** — JWT, OAuth 2.0 (Google, GitHub, Microsoft, custom OIDC), LDAP
- **Role-Based Access Control** — Admin and user roles with granular permissions
- **Group Management** — Organize users into groups with shared access control
- **API Keys** — Long-lived tokens for programmatic access
- **Audit & Analytics** — Usage tracking, token consumption, model utilization dashboards

### Memory & Personalization
- **User Memory** — Persistent memory storage for personalized AI interactions
- **Prompt Templates** — Reusable prompts with version history and rollback
- **Model Aliases** — Create custom model configurations with parameter overrides
- **Per-User Settings** — UI preferences, default models, function/tool configurations

---

## Part II: Technical Overview

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend Framework** | SvelteKit | 2.5.27 | Meta-framework for Svelte |
| **Frontend UI** | Svelte | 5.0.0 | Reactive component framework |
| **Frontend Styling** | Tailwind CSS | 4.0.0 | Utility-first CSS |
| **Frontend Build** | Vite | 5.4.21 | Development server and bundler |
| **Frontend Language** | TypeScript | 5.5.4 | Type-safe JavaScript |
| **Backend Framework** | FastAPI | 0.128.0 | Async Python web framework |
| **Backend Server** | Uvicorn | — | ASGI server |
| **Backend Language** | Python | 3.11-3.12 | Backend runtime |
| **Database ORM** | SQLAlchemy | 2.0.46 | Database abstraction |
| **Database Migration** | Alembic | 1.18.3 | Schema versioning |
| **Default Database** | SQLite | — | File-based SQL database |
| **Production Database** | PostgreSQL/MySQL | — | Scalable SQL databases |
| **Real-Time** | Socket.IO | 5.16.0 | WebSocket abstraction |
| **Distributed State** | Redis | — | Session/cache for multi-instance |
| **Vector Database** | ChromaDB | — | Default embedding storage |
| **Embeddings** | sentence-transformers | — | Text embedding models |
| **Document Loading** | LangChain | — | Document processing pipeline |
| **Observability** | OpenTelemetry | — | Distributed tracing |

### Architecture Snapshot

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (SvelteKit)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Routes    │  │ Components  │  │   Stores    │  │ API Clients │        │
│  │  /src/routes│  │/src/lib/    │  │/src/lib/    │  │/src/lib/apis│        │
│  │             │  │components   │  │stores       │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ REST API + SSE + WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Routers   │  │   Models    │  │   Utils     │  │   Socket    │        │
│  │  /routers   │  │  /models    │  │  /utils     │  │  /socket    │        │
│  │  (25+ APIs) │  │ (20 tables) │  │ (auth,etc)  │  │ (real-time) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │  Retrieval  │  │  Storage    │  │ Middleware  │                         │
│  │ /retrieval  │  │  /storage   │  │ /utils/     │                         │
│  │ (RAG/vector)│  │ (files)     │  │ middleware  │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             ┌───────────┐     ┌───────────┐     ┌───────────┐
             │  Database │     │Vector DB  │     │LLM Providers│
             │SQLite/PG  │     │ChromaDB/  │     │OpenAI/Ollama│
             │/MySQL     │     │Qdrant/etc │     │/Anthropic   │
             └───────────┘     └───────────┘     └───────────┘
```

### Key Metrics

| Metric | Count |
|--------|-------|
| Backend Routers | 25+ |
| Database Models | 20 |
| Frontend Routes | 15+ |
| Frontend Stores | 30+ |
| API Client Modules | 26 |
| Alembic Migrations | 60+ |

---

## Part III: Key Subsystems

### LLM Provider Abstraction

The system abstracts multiple LLM providers behind a unified interface. Requests flow through middleware that:

1. Applies system prompts and model-specific parameters
2. Forwards to the appropriate provider (OpenAI, Ollama, etc.)
3. Streams responses back via SSE
4. Logs usage statistics for analytics

**Key Files:**
- `backend/open_webui/routers/openai.py` — OpenAI-compatible endpoint proxy
- `backend/open_webui/routers/ollama.py` — Ollama-specific integration
- `backend/open_webui/utils/middleware.py` — Request/response transformation

### RAG Pipeline

Document retrieval follows this flow:

1. **Ingestion:** Documents uploaded → parsed by loaders → chunked
2. **Embedding:** Chunks → sentence-transformer → vector embeddings
3. **Storage:** Embeddings stored in vector database (ChromaDB default)
4. **Retrieval:** Query → embed → similarity search → top-k chunks
5. **Injection:** Retrieved chunks injected into LLM context

**Key Files:**
- `backend/open_webui/retrieval/loaders/` — Document type loaders
- `backend/open_webui/retrieval/vector/` — Vector DB integrations
- `backend/open_webui/routers/retrieval.py` — RAG API endpoints

### Real-Time Communication

Socket.IO powers real-time features:

- **Message streaming** — Token-by-token response delivery
- **Usage tracking** — Live model utilization across users
- **Channel messaging** — Group chat and DM functionality
- **Collaborative editing** — YCRDT-based document sync

**Key Files:**
- `backend/open_webui/socket/main.py` — Socket.IO server and events
- `backend/open_webui/socket/utils.py` — Redis-backed distributed state

### Authentication System

Multi-strategy authentication supporting:

- **Local auth** — Email/password with bcrypt/argon2 hashing
- **JWT tokens** — Stateless API authentication
- **OAuth 2.0/OIDC** — External identity providers
- **LDAP** — Enterprise directory integration
- **API keys** — Programmatic access tokens

**Key Files:**
- `backend/open_webui/routers/auths.py` — Auth endpoints
- `backend/open_webui/utils/auth.py` — Token validation and user extraction
- `backend/open_webui/models/auths.py` — Auth data models

### Analytics Subsystem

Recently introduced analytics tracking:

- **Message-level metrics** — Token usage per message
- **Model utilization** — Requests and tokens by model
- **User activity** — Per-user consumption statistics
- **Time-series data** — Daily/hourly aggregations

**Key Files:**
- `backend/open_webui/routers/analytics.py` — Analytics API
- `backend/open_webui/models/chat_messages.py` — Message analytics table

---

## Part IV: Project Structure

```
open-webui/
├── PRODUCT_OVERVIEW.md          # This file
├── README.md                    # Setup and running instructions
│
├── docs/                        # Documentation (see DOCUMENTATION_INDEX.md)
│   ├── DOCUMENTATION_INDEX.md   # Visual map of all documentation
│   ├── RETRIEVAL_DIRECTIVE.md   # AI agent navigation protocol
│   ├── DOMAIN_GLOSSARY.md       # Business → code term mapping
│   ├── DATA_MODEL.md            # Entity relationships
│   ├── DATABASE_SCHEMA.md       # Field-level schema reference
│   ├── ARCHITECTURE_OVERVIEW.md # System design
│   ├── SYSTEM_TOPOLOGY.md       # Runtime behavior
│   ├── TESTING_STRATEGY.md      # Test patterns
│   ├── adr/                     # Architecture Decision Records
│   └── directives/              # How-to procedural guides
│
├── backend/                     # Python FastAPI backend
│   └── open_webui/
│       ├── main.py              # Application entry point
│       ├── config.py            # Runtime configuration
│       ├── env.py               # Environment variable loading
│       ├── routers/             # API endpoints (25+ modules)
│       ├── models/              # SQLAlchemy ORM models
│       ├── socket/              # WebSocket/Socket.IO server
│       ├── retrieval/           # RAG and vector search
│       ├── storage/             # File storage handling
│       ├── utils/               # Utilities (auth, middleware, etc.)
│       └── migrations/          # Alembic database migrations
│
├── src/                         # SvelteKit frontend
│   ├── routes/                  # File-based routing
│   │   ├── +layout.svelte       # Root layout
│   │   ├── (app)/               # Protected app routes
│   │   ├── auth/                # Authentication pages
│   │   └── admin/               # Admin panel
│   └── lib/
│       ├── components/          # Reusable UI components
│       ├── stores/              # Svelte stores (state)
│       ├── apis/                # Backend API clients
│       ├── utils/               # Frontend utilities
│       └── types/               # TypeScript definitions
│
├── Dockerfile                   # Multi-stage container build
├── docker-compose.yaml          # Container orchestration
├── package.json                 # Node.js dependencies
├── pyproject.toml               # Python dependencies
└── svelte.config.js             # SvelteKit configuration
```

---

## Documentation

For detailed documentation, see the `/docs` folder:

| Document | Purpose |
|----------|---------|
| `DOCUMENTATION_INDEX.md` | Visual map and quick lookup |
| `RETRIEVAL_DIRECTIVE.md` | AI navigation protocol |
| `DOMAIN_GLOSSARY.md` | Term definitions |
| `DATA_MODEL.md` | Entity relationships |
| `ARCHITECTURE_OVERVIEW.md` | System design |
| `directives/*.md` | How-to guides |
| `adr/*.md` | Decision records |

---

*Last updated: 2026-02-03*
