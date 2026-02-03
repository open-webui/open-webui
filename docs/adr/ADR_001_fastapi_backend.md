# ADR 001: FastAPI Backend Framework

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI requires a backend framework to:
- Serve REST APIs for the frontend
- Handle WebSocket connections for real-time features
- Process LLM requests with streaming responses
- Manage database operations
- Support async operations for high concurrency

The backend needs to handle many concurrent connections efficiently, as users may have multiple chat sessions active simultaneously, each potentially streaming responses.

## Decision

Use **FastAPI** as the backend framework with **Uvicorn** as the ASGI server.

Key characteristics leveraged:
- Native async/await support (critical for LLM streaming)
- Automatic OpenAPI documentation generation
- Pydantic integration for request/response validation
- High performance via Starlette foundation
- WebSocket support out of the box

## Consequences

### Positive
- **Async performance:** Native coroutine support enables efficient handling of many concurrent LLM streams
- **Type safety:** Pydantic models catch API contract violations early
- **Documentation:** Auto-generated Swagger UI at `/docs` aids development and debugging
- **Ecosystem:** Large ecosystem of compatible libraries (SQLAlchemy async, aiohttp, etc.)
- **Learning curve:** Python is accessible to contributors

### Negative
- **GIL limitations:** CPU-bound tasks (embedding generation) can block; mitigated by offloading to workers
- **Memory footprint:** Higher per-process memory than Go/Rust alternatives
- **Deployment complexity:** Requires ASGI server configuration, worker management

### Neutral
- Python version constraints (3.11+) limit some deployment environments
- Requires understanding of async patterns for effective development

## Implementation

**Entry point:** `backend/open_webui/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
# ... additional routers
```

**Running:**
```bash
uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --workers 1
```

## Alternatives Considered

### Flask
- Simpler but lacks native async support
- Would require Celery/threading for concurrent LLM streams
- Rejected due to async limitations

### Django
- Full-featured but heavier than needed
- Async support added later, not native
- Rejected due to complexity and sync-first design

### Go (Gin/Echo)
- Better raw performance
- Harder to find AI/ML library support
- Rejected due to ecosystem limitations for LLM integration

### Node.js (Express/Fastify)
- Good async model
- Weaker ML/AI library ecosystem compared to Python
- Rejected due to Python being standard for AI tooling

## Related Documents

- `ARCHITECTURE_OVERVIEW.md` — System design overview
- `ADR_005_socketio_realtime.md` — Real-time architecture built on FastAPI

---

*Last updated: 2026-02-03*
