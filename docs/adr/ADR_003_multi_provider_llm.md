# ADR 003: Multi-Provider LLM Abstraction

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI needs to support multiple LLM providers:
- **Ollama:** Local model hosting
- **OpenAI:** GPT models via API
- **Anthropic:** Claude models
- **Google:** Gemini models
- **Azure OpenAI:** Enterprise deployments
- **Custom endpoints:** Any OpenAI-compatible API

Users may want to:
- Switch between providers based on task
- Use local models for privacy, cloud for capability
- Compare responses across providers
- Self-host without external dependencies

## Decision

Implement a **provider-agnostic abstraction layer** that:
1. Normalizes all providers to OpenAI-compatible request/response format
2. Routes requests through middleware for consistent processing
3. Handles streaming via Server-Sent Events (SSE)
4. Manages provider-specific authentication and configuration

Key design:
- **Unified API:** Frontend calls `/api/chat/completions` regardless of provider
- **Provider routers:** Separate routers handle provider-specific logic
- **Middleware transformation:** Requests/responses normalized in middleware
- **Configuration-driven:** Provider URLs and keys set via environment/admin UI

## Consequences

### Positive
- **User flexibility:** Switch providers without UI changes
- **Feature parity:** All providers support same chat interface
- **Extensibility:** New providers added by implementing router pattern
- **Model comparison:** Easy A/B testing across providers

### Negative
- **Lowest common denominator:** Some provider-specific features not exposed
- **Complexity:** Middleware layer adds processing overhead
- **Debugging:** Request flow through multiple layers harder to trace
- **Provider drift:** Must track API changes across multiple providers

### Neutral
- Configuration complexity increases with provider count
- Documentation must cover each provider's setup

## Implementation

**Request flow:**
```
Frontend
    │
    ▼
/api/chat/completions (main.py)
    │
    ▼
Middleware (utils/middleware.py)
    ├── Apply system prompt
    ├── Inject RAG context
    ├── Apply model parameters
    │
    ▼
Provider Router (routers/openai.py or ollama.py)
    │
    ▼
External Provider API
    │
    ▼
Streaming Response (SSE)
    │
    ▼
Frontend (token-by-token rendering)
```

**Provider router pattern:**

```python
# routers/openai.py
router = APIRouter()

@router.post("/api/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    user: UserModel = Depends(get_verified_user)
):
    # Build headers for OpenAI API
    headers = await get_headers_and_cookies(request, url, key)

    # Forward to provider
    response = await aiohttp.post(url, json=body, headers=headers)

    # Stream response back
    return StreamingResponse(
        stream_content(response),
        media_type="text/event-stream"
    )
```

**Configuration:**

```python
# Environment variables
OPENAI_API_BASE_URLS=["https://api.openai.com/v1"]
OPENAI_API_KEYS=["sk-..."]
OLLAMA_BASE_URLS=["http://localhost:11434"]

# Runtime configuration
app.state.config.OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS
app.state.config.OPENAI_API_KEYS = OPENAI_API_KEYS
```

## Alternatives Considered

### LangChain Abstraction
- Provides multi-provider support out of box
- Adds significant dependency weight
- Less control over streaming behavior
- Rejected for being too heavyweight

### Provider-Specific UIs
- Separate chat interfaces per provider
- Simpler implementation per provider
- Poor user experience switching between
- Rejected due to UX fragmentation

### GraphQL Federation
- Single API layer federating provider APIs
- Significant architectural complexity
- Overkill for request forwarding use case
- Rejected due to complexity

## Related Documents

- `DIRECTIVE_adding_llm_provider.md` — How to add new providers
- `ARCHITECTURE_OVERVIEW.md` — System design
- `SYSTEM_TOPOLOGY.md` — Request flow details

---

*Last updated: 2026-02-03*
