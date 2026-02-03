# System Topology

> **Purpose:** Runtime behavior, data flows, and service interactions
> **Audience:** Developers debugging issues or understanding runtime behavior
> **Usage:** Reference when tracing request flows or diagnosing problems

---

## Prerequisites

- `ARCHITECTURE_OVERVIEW.md` — Component structure
- `DOMAIN_GLOSSARY.md` — Term definitions

---

## Request Flow: Chat Completion

The most common flow in the application:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. USER SENDS MESSAGE                                                            │
│                                                                                  │
│    User types message in chat interface                                          │
│    ↓                                                                             │
│    Frontend calls: POST /api/chat/completions                                    │
│    {                                                                             │
│      "model": "gpt-4o",                                                         │
│      "messages": [{"role": "user", "content": "Hello"}],                        │
│      "stream": true                                                              │
│    }                                                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. AUTHENTICATION                                                                │
│                                                                                  │
│    get_verified_user() dependency:                                              │
│    • Extract token from Authorization header or cookie                          │
│    • Decode JWT, verify signature and expiration                                │
│    • Load user from database                                                    │
│    • Return UserModel or raise 401                                              │
│                                                                                  │
│    File: backend/open_webui/utils/auth.py                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. MIDDLEWARE PROCESSING                                                         │
│                                                                                  │
│    File: backend/open_webui/utils/middleware.py                                 │
│                                                                                  │
│    a) System Prompt Injection                                                    │
│       • Prepend configured system prompt                                         │
│       • Add user context if enabled                                              │
│                                                                                  │
│    b) RAG Context Injection (if knowledge base selected)                        │
│       • Embed user query                                                        │
│       • Search vector database                                                  │
│       • Inject top-k chunks into messages                                       │
│                                                                                  │
│    c) Model Parameters                                                           │
│       • Apply model-specific settings                                           │
│       • Override defaults with user preferences                                 │
│                                                                                  │
│    d) Function Filters (if enabled)                                              │
│       • Run inlet() on active filter functions                                  │
│       • May modify request body                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. PROVIDER ROUTING                                                              │
│                                                                                  │
│    File: backend/open_webui/routers/openai.py (or ollama.py)                   │
│                                                                                  │
│    • Determine provider from model ID                                           │
│    • Build provider-specific headers (API key, etc.)                           │
│    • Forward request to provider API                                            │
│                                                                                  │
│    Provider selection:                                                           │
│    ┌─────────────┬───────────────────────────────┐                             │
│    │ Model prefix│ Provider                       │                             │
│    ├─────────────┼───────────────────────────────┤                             │
│    │ gpt-*       │ OpenAI API                     │                             │
│    │ llama*      │ Ollama (local)                 │                             │
│    │ claude-*    │ Anthropic API                  │                             │
│    │ gemini-*    │ Google AI                      │                             │
│    │ custom/*    │ Configured OpenAI-compatible   │                             │
│    └─────────────┴───────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. STREAMING RESPONSE                                                            │
│                                                                                  │
│    Provider streams tokens via Server-Sent Events (SSE)                         │
│                                                                                  │
│    Stream format:                                                                │
│    data: {"choices":[{"delta":{"content":"Hello"}}]}                           │
│    data: {"choices":[{"delta":{"content":" there"}}]}                          │
│    data: {"choices":[{"delta":{"content":"!"}}]}                               │
│    data: [DONE]                                                                  │
│                                                                                  │
│    Backend passes through to frontend                                           │
│    File: Uses FastAPI StreamingResponse                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. FRONTEND RENDERING                                                            │
│                                                                                  │
│    File: src/lib/apis/index.ts (chatCompletion function)                        │
│                                                                                  │
│    • Parse SSE stream                                                           │
│    • Update message content token-by-token                                      │
│    • Trigger Svelte reactivity for live display                                │
│    • Handle tool calls if present                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 7. PERSISTENCE                                                                   │
│                                                                                  │
│    On stream completion:                                                         │
│                                                                                  │
│    a) Update Chat.chat JSON (legacy storage)                                    │
│       • Add message to history.messages                                         │
│       • Update currentId pointer                                                │
│       File: backend/open_webui/models/chats.py                                  │
│                                                                                  │
│    b) Insert ChatMessage record (analytics)                                     │
│       • Store role, content, model_id, usage                                    │
│       File: backend/open_webui/models/chat_messages.py                          │
│                                                                                  │
│    c) Update usage tracking (Socket.IO)                                         │
│       • Emit usage event for real-time dashboard                                │
│       File: backend/open_webui/socket/main.py                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: RAG Retrieval

When a knowledge base is selected:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. DOCUMENT UPLOAD                                                               │
│                                                                                  │
│    POST /api/v1/files/upload                                                    │
│    ↓                                                                             │
│    • Save file to storage (local/S3)                                           │
│    • Create File record in database                                             │
│    • Associate with Knowledge base                                              │
│                                                                                  │
│    Files: backend/open_webui/routers/files.py                                   │
│           backend/open_webui/storage/provider.py                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. DOCUMENT PROCESSING                                                           │
│                                                                                  │
│    POST /api/v1/retrieval/process                                              │
│    ↓                                                                             │
│    a) Load document using appropriate loader                                    │
│       • PDF → PDFLoader                                                         │
│       • DOCX → DocxLoader                                                       │
│       • YouTube → YoutubeLoader                                                 │
│       • etc.                                                                    │
│       File: backend/open_webui/retrieval/loaders/                              │
│                                                                                  │
│    b) Chunk document                                                            │
│       • Split into chunks (default: 1500 chars, 100 overlap)                   │
│       • Maintain metadata (source, page number)                                │
│                                                                                  │
│    c) Generate embeddings                                                       │
│       • Use sentence-transformer model                                         │
│       • Default: all-MiniLM-L6-v2                                              │
│       File: backend/open_webui/retrieval/utils.py                              │
│                                                                                  │
│    d) Store in vector database                                                  │
│       • ChromaDB (default) / Qdrant / Pinecone / etc.                         │
│       • Index by collection (knowledge base ID)                                │
│       File: backend/open_webui/retrieval/vector/                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. QUERY-TIME RETRIEVAL                                                          │
│                                                                                  │
│    During chat completion (middleware):                                          │
│    ↓                                                                             │
│    a) Embed user query                                                          │
│       • Same model as document embeddings                                       │
│                                                                                  │
│    b) Vector similarity search                                                  │
│       • Find top-k similar chunks (default: k=5)                               │
│       • Score by cosine similarity                                             │
│                                                                                  │
│    c) Optional: Hybrid search                                                   │
│       • BM25 keyword search                                                    │
│       • Combine with vector results                                            │
│                                                                                  │
│    d) Optional: Reranking                                                       │
│       • Rerank results with cross-encoder                                      │
│       • Improve relevance                                                      │
│                                                                                  │
│    e) Context injection                                                         │
│       • Format chunks as context                                               │
│       • Inject into system prompt or messages                                  │
│                                                                                  │
│    File: backend/open_webui/routers/retrieval.py                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: WebSocket Communication

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. CONNECTION ESTABLISHMENT                                                      │
│                                                                                  │
│    Client connects to: /ws/socket.io                                            │
│    ↓                                                                             │
│    • Socket.IO handshake                                                        │
│    • Auth token validation                                                      │
│    • User added to SESSION_POOL                                                 │
│    • User joins personal room: user:{user_id}                                  │
│                                                                                  │
│    File: backend/open_webui/socket/main.py                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. EVENT HANDLING                                                                │
│                                                                                  │
│    Client emits events:                                                          │
│    ┌────────────────┬─────────────────────────────────────┐                     │
│    │ Event          │ Handler                              │                     │
│    ├────────────────┼─────────────────────────────────────┤                     │
│    │ usage          │ Track model usage in USAGE_POOL     │                     │
│    │ user-join      │ Join room for context               │                     │
│    │ join-channels  │ Subscribe to channel updates        │                     │
│    │ join-note      │ Join collaborative note session     │                     │
│    │ heartbeat      │ Keep connection alive               │                     │
│    └────────────────┴─────────────────────────────────────┘                     │
│                                                                                  │
│    Server emits events:                                                          │
│    ┌────────────────┬─────────────────────────────────────┐                     │
│    │ Event          │ Purpose                              │                     │
│    ├────────────────┼─────────────────────────────────────┤                     │
│    │ message        │ New channel message                  │                     │
│    │ model:status   │ Model availability change           │                     │
│    │ user:status    │ User presence update                │                     │
│    │ notification   │ System notification                 │                     │
│    └────────────────┴─────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. DISTRIBUTED MODE (Redis)                                                      │
│                                                                                  │
│    When WEBSOCKET_MANAGER=redis:                                                │
│    ↓                                                                             │
│    • Socket.IO uses Redis adapter                                               │
│    • Events published to Redis Pub/Sub                                          │
│    • All instances receive and broadcast                                        │
│    • SESSION_POOL backed by RedisDict                                           │
│                                                                                  │
│    File: backend/open_webui/socket/utils.py                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: Authentication

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. LOCAL AUTHENTICATION                                                          │
│                                                                                  │
│    POST /api/v1/auths/signin                                                   │
│    { "email": "...", "password": "..." }                                       │
│    ↓                                                                             │
│    • Lookup user by email                                                       │
│    • Verify password hash (bcrypt/argon2)                                      │
│    • Generate JWT token                                                         │
│    • Set cookie and return token                                               │
│                                                                                  │
│    File: backend/open_webui/routers/auths.py                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. OAUTH AUTHENTICATION                                                          │
│                                                                                  │
│    GET /api/v1/auths/oauth/{provider}/login                                    │
│    ↓                                                                             │
│    • Redirect to provider authorization URL                                     │
│    • User authenticates with provider                                          │
│    ↓                                                                             │
│    GET /api/v1/auths/oauth/{provider}/callback                                 │
│    ↓                                                                             │
│    • Exchange code for tokens                                                   │
│    • Fetch user info from provider                                             │
│    • Find or create local user                                                 │
│    • Generate JWT token                                                         │
│    • Redirect to app with cookie set                                           │
│                                                                                  │
│    File: backend/open_webui/routers/auths.py                                   │
│           backend/open_webui/utils/oauth.py                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. TOKEN VALIDATION (every request)                                              │
│                                                                                  │
│    Authorization: Bearer {token}                                                │
│    ↓                                                                             │
│    • Decode JWT                                                                 │
│    • Verify signature with WEBUI_SECRET_KEY                                    │
│    • Check expiration                                                          │
│    • Load user from database                                                   │
│    • Check user.active status                                                  │
│                                                                                  │
│    File: backend/open_webui/utils/auth.py                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ ERROR PROPAGATION                                                                │
│                                                                                  │
│    1. Exception raised in handler                                               │
│       ↓                                                                          │
│    2. FastAPI exception handler catches                                         │
│       ↓                                                                          │
│    3. Error formatted as JSON response:                                         │
│       {                                                                          │
│         "detail": "Error message",                                              │
│         "code": "ERROR_CODE" (optional)                                        │
│       }                                                                          │
│       ↓                                                                          │
│    4. Frontend API client catches:                                              │
│       • Logs error                                                              │
│       • Throws to caller                                                        │
│       ↓                                                                          │
│    5. Component handles:                                                         │
│       • Shows error message                                                     │
│       • Optionally retries                                                      │
│                                                                                  │
│    Common HTTP status codes:                                                     │
│    ┌──────┬─────────────────────────────────────────┐                           │
│    │ Code │ Meaning                                  │                           │
│    ├──────┼─────────────────────────────────────────┤                           │
│    │ 400  │ Bad request (validation error)          │                           │
│    │ 401  │ Not authenticated                       │                           │
│    │ 403  │ Not authorized (wrong role)             │                           │
│    │ 404  │ Resource not found                      │                           │
│    │ 422  │ Validation error (Pydantic)             │                           │
│    │ 500  │ Internal server error                   │                           │
│    │ 502  │ Provider error (LLM API failure)        │                           │
│    └──────┴─────────────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEPENDENCY GRAPH                                    │
│                                                                                  │
│                          ┌──────────────────┐                                   │
│                          │   Open WebUI     │                                   │
│                          │   Application    │                                   │
│                          └────────┬─────────┘                                   │
│                                   │                                              │
│          ┌────────────────────────┼────────────────────────┐                    │
│          │                        │                        │                    │
│          ▼                        ▼                        ▼                    │
│  ┌───────────────┐       ┌───────────────┐       ┌───────────────┐             │
│  │   Required    │       │   Required    │       │   Optional    │             │
│  │               │       │               │       │               │             │
│  │  • Database   │       │  • LLM API    │       │  • Redis      │             │
│  │    (SQLite/   │       │    (OpenAI/   │       │  • Vector DB  │             │
│  │     PG/MySQL) │       │    Ollama)    │       │  • S3 Storage │             │
│  │               │       │               │       │  • LDAP       │             │
│  └───────────────┘       └───────────────┘       └───────────────┘             │
│                                                                                  │
│  Startup order:                                                                  │
│  1. Database connection (migrations auto-run)                                   │
│  2. Redis connection (if configured)                                            │
│  3. Vector DB connection (if configured)                                        │
│  4. LLM provider health check (optional)                                        │
│  5. Socket.IO initialization                                                    │
│  6. Start accepting requests                                                    │
│                                                                                  │
│  Health check: GET /health                                                      │
│  Returns: {"status": true}                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Debugging Reference

### Common Issues

| Symptom | Likely Cause | Investigation Path |
|---------|--------------|-------------------|
| 401 on all requests | Invalid token | Check WEBUI_SECRET_KEY, token expiration |
| WebSocket disconnects | Token expired | Check token refresh, cookie settings |
| Slow RAG retrieval | Large embeddings | Check vector DB performance, chunk count |
| Missing messages | Dual-write failure | Check both Chat.chat and chat_messages |
| OAuth redirect fails | Callback URL mismatch | Verify WEBUI_URL matches OAuth config |

### Key Log Locations

| Component | Log Source |
|-----------|------------|
| FastAPI | stdout/stderr |
| Uvicorn | stdout |
| SQLAlchemy | `logging.getLogger('sqlalchemy')` |
| Socket.IO | `logging.getLogger('socketio')` |
| Application | `logging.getLogger('open_webui')` |

---

## Related Documents

- `ARCHITECTURE_OVERVIEW.md` — Component structure
- `DOMAIN_GLOSSARY.md` — Term definitions
- ADRs — Design decision context

---

*Last updated: 2026-02-03*
