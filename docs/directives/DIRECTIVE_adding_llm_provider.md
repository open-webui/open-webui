# Directive: Adding a New LLM Provider

> **Pattern type:** Backend integration
> **Complexity:** Medium-High
> **Files touched:** 3-5

---

## Prerequisites

- `ADR_003_multi_provider_llm.md` — LLM abstraction architecture
- `SYSTEM_TOPOLOGY.md` — Request flow understanding

---

## Structural Pattern

When integrating a new LLM provider, implement the OpenAI-compatible abstraction layer:

1. **Create provider router** that handles provider-specific API calls
2. **Implement streaming** for token-by-token response delivery
3. **Configure environment variables** for API keys and base URLs
4. **Register with model discovery** so provider models appear in UI

| Component | Location | Purpose |
|-----------|----------|---------|
| Provider router | `backend/open_webui/routers/{provider}.py` | API proxy |
| Configuration | `backend/open_webui/config.py` | Runtime settings |
| Environment | `backend/open_webui/env.py` | Environment loading |
| Model list | Provider API or static config | Available models |

---

## Illustrative Application

The OpenAI router (`backend/open_webui/routers/openai.py`) demonstrates this pattern:

### Step 1: Create Provider Router

```python
# backend/open_webui/routers/{provider}.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
import aiohttp
import json

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.config import PROVIDER_API_KEY, PROVIDER_BASE_URL

router = APIRouter()


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[dict]
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


async def stream_response(response) -> AsyncGenerator[str, None]:
    """Stream SSE chunks from provider response."""
    async for line in response.content:
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith('data: '):
                yield decoded
    yield "data: [DONE]\n\n"


@router.get("/models")
async def get_models(user: UserModel = Depends(get_verified_user)):
    """List available models from this provider."""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {PROVIDER_API_KEY}"}
        async with session.get(
            f"{PROVIDER_BASE_URL}/models",
            headers=headers
        ) as response:
            data = await response.json()
            return data


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    user: UserModel = Depends(get_verified_user),
):
    """Proxy chat completions to provider."""
    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{PROVIDER_BASE_URL}/chat/completions",
            headers=headers,
            json=body.model_dump(),
        ) as response:
            if body.stream:
                return StreamingResponse(
                    stream_response(response),
                    media_type="text/event-stream",
                )
            else:
                return await response.json()
```

### Step 2: Add Configuration

```python
# backend/open_webui/env.py

# Add environment variable loading
PROVIDER_API_KEY = os.environ.get("PROVIDER_API_KEY", "")
PROVIDER_BASE_URL = os.environ.get(
    "PROVIDER_BASE_URL",
    "https://api.provider.com/v1"
)
ENABLE_PROVIDER = os.environ.get("ENABLE_PROVIDER", "true").lower() == "true"
```

```python
# backend/open_webui/config.py

# Add runtime configuration
from open_webui.env import (
    PROVIDER_API_KEY,
    PROVIDER_BASE_URL,
    ENABLE_PROVIDER,
)

# Make available on app state
# app.state.config.PROVIDER_API_KEY = PROVIDER_API_KEY
```

### Step 3: Register Router

```python
# backend/open_webui/main.py

from open_webui.routers import provider

if ENABLE_PROVIDER:
    app.include_router(
        provider.router,
        prefix="/api/v1/provider",
        tags=["provider"]
    )
```

### Step 4: Add to Model Aggregation

```python
# backend/open_webui/routers/models.py

# In get_models() function, add provider models to aggregated list
async def get_all_models():
    models = []

    # Existing providers...

    # Add new provider
    if ENABLE_PROVIDER:
        provider_models = await get_provider_models()
        models.extend(provider_models)

    return models
```

---

## Transfer Prompt

**When you need to integrate a new LLM provider:**

1. **Create router file:** `backend/open_webui/routers/{provider}.py`

2. **Implement required endpoints:**
   - `GET /models` — List available models
   - `POST /chat/completions` — Chat completion with streaming

3. **Handle streaming correctly:**
   ```python
   from fastapi.responses import StreamingResponse

   async def stream_response(provider_response):
       async for chunk in provider_response:
           # Transform to OpenAI SSE format if needed
           yield f"data: {json.dumps(chunk)}\n\n"
       yield "data: [DONE]\n\n"

   return StreamingResponse(
       stream_response(response),
       media_type="text/event-stream"
   )
   ```

4. **Add environment configuration:**
   - `{PROVIDER}_API_KEY` — API authentication
   - `{PROVIDER}_BASE_URL` — API endpoint
   - `ENABLE_{PROVIDER}` — Feature flag

5. **Register in main.py** with feature flag check

6. **Add to model aggregation** in `routers/models.py`

7. **Test streaming** by sending a chat request and verifying token-by-token delivery

**Provider-specific considerations:**
- Some providers use different auth methods (API key vs OAuth)
- Response formats may need transformation to OpenAI format
- Rate limiting and error handling may differ
- Model naming conventions vary

**Signals that this pattern applies:**
- User requests support for a new AI provider
- Need to integrate self-hosted model server
- Adding enterprise-specific provider

---

## Related Documents

- `ADR_003_multi_provider_llm.md` — Architecture rationale
- `DIRECTIVE_adding_api_router.md` — Basic router pattern
- `SYSTEM_TOPOLOGY.md` — Full request flow

---

*Last updated: 2026-02-03*
