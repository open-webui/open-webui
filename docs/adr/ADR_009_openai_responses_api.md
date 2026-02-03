# ADR 009: Multi-Format OpenAI API Compatibility

> **Status:** Accepted (Experimental)
> **Date:** 2026-01 (commit: ea9c58e)
> **Deciders:** Open WebUI contributors

## Context

OpenAI introduced a new "Responses API" format alongside the existing Chat Completions API. The new format offers:
- Different response structure
- Additional capabilities for certain use cases
- Potential future direction for OpenAI APIs

Open WebUI needed to support both formats to:
- Maintain compatibility with existing Chat Completions workflows
- Enable users to leverage new Responses API features
- Provide flexibility for different provider configurations

## Decision

Extend the middleware layer to **support multiple OpenAI API formats** through:
1. Connection-level API format configuration
2. Middleware transformation based on selected format
3. Response normalization for consistent frontend handling

Key design:
- **Configuration per connection:** Each OpenAI-compatible connection can specify its API format
- **Middleware handles transformation:** Request/response adapted based on format
- **Experimental flag:** Feature marked experimental pending wider adoption

## Consequences

### Positive
- **Forward compatibility:** Ready for OpenAI API evolution
- **User choice:** Different connections can use different formats
- **Provider flexibility:** Works with providers implementing either format

### Negative
- **Complexity increase:** Middleware now handles multiple code paths
- **Testing burden:** Both formats need comprehensive testing
- **Documentation:** Users need to understand format differences
- **Maintenance:** Must track changes to both API formats

### Neutral
- Marked as experimental; may change based on OpenAI direction
- Default remains Chat Completions for stability

## Implementation

**Connection configuration:**

```typescript
// Frontend connection modal
interface Connection {
  url: string;
  key: string;
  apiFormat: 'chat_completions' | 'responses';  // New field
}
```

**Middleware transformation:**

```python
# utils/middleware.py
async def process_request(request: dict, api_format: str) -> dict:
    """Transform request based on API format."""
    if api_format == "responses":
        return transform_to_responses_format(request)
    return request  # Chat completions (default)

async def process_response(response: AsyncIterator, api_format: str) -> AsyncIterator:
    """Normalize response regardless of format."""
    if api_format == "responses":
        async for chunk in response:
            yield normalize_responses_chunk(chunk)
    else:
        async for chunk in response:
            yield chunk
```

**Router integration:**

```python
# routers/openai.py
@router.post("/api/chat/completions")
async def chat_completions(request: Request, body: dict):
    # Get connection config
    connection = get_connection_config(body.get("model"))
    api_format = connection.get("api_format", "chat_completions")

    # Transform request
    transformed = await process_request(body, api_format)

    # Forward to provider
    response = await forward_to_provider(connection, transformed)

    # Stream normalized response
    return StreamingResponse(
        process_response(response, api_format),
        media_type="text/event-stream"
    )
```

## Migration

No migration required. Existing connections default to `chat_completions` format.

Users can opt-in to `responses` format per connection via the connection modal.

## Alternatives Considered

### Separate endpoints per format
- `/api/chat/completions` and `/api/responses`
- Cleaner separation
- Requires frontend changes for format selection
- Rejected for user experience complexity

### Auto-detect format from response
- Automatically determine format from provider response
- No configuration needed
- Unreliable detection, edge cases
- Rejected for reliability concerns

### Wait for API stabilization
- Don't implement until format is stable
- Less maintenance burden
- Users can't use new features
- Rejected for user flexibility

## Related Documents

- `DIRECTIVE_adding_llm_provider.md` — Provider integration patterns
- `ADR_003_multi_provider_llm.md` — Provider abstraction architecture
- `SYSTEM_TOPOLOGY.md` — Request flow through middleware

---

*Last updated: 2026-02-03*
