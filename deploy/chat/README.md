# chat.jawafdehi.org — jawafdehi-mcp Integration

Service definition and OpenWebUI config to add jawafdehi-mcp (HTTP mode)
to the chat.jawafdehi.org stack.

## Architecture

```
User → Google OAuth → OpenWebUI
                         │
                         │  Custom Headers:
                         │  X-Jawafdehi-User-Id: {{USER_ID}}
                         │  X-Jawafdehi-User-Name: {{USER_NAME}}
                         │
                         ▼  http://jawafdehi-mcp:8000  (internal Docker network)
                  jawafdehi-mcp (Streamable HTTP)
                         │
                         │  Forwards headers + service account token
                         ▼
                  jawafdehi-api (resolves identity, enforces permissions)
```

No nginx needed — jawafdehi-mcp runs on an unexposed port on the same Docker
network as OpenWebUI. There is no external path for header spoofing.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | jawafdehi-mcp service definition (add to existing OpenWebUI compose) |
| `openwebui/tools-config.json` | OpenWebUI External Tools MCP server config |
| `mcp.env.example` | Template for jawafdehi-mcp environment variables |

## Quick Start

1. Set up the service account on the jawafdehi-api server:
   ```bash
   python manage.py migrate
   python manage.py setup_chat_service_account
   ```

2. Copy the environment template and fill in credentials:
   ```bash
   cp mcp.env.example mcp.env
   # Edit mcp.env — set JAWAFDEHI_API_TOKEN from step 1
   ```

3. Add the `jawafdehi-mcp` service definition from `docker-compose.yml`
   to the existing OpenWebUI docker-compose, then restart:
   ```bash
   docker compose up -d
   ```

4. Configure OpenWebUI:
   - Go to Admin Settings → External Tools
   - Import the MCP server config from `openwebui/tools-config.json`

## Identity Flow

1. OpenWebUI authenticates users via Google OAuth
2. `{{USER_ID}}` and `{{USER_NAME}}` tokens are resolved at request time
3. OpenWebUI sends these as `X-Jawafdehi-User-Id` and `X-Jawafdehi-User-Name` headers directly to jawafdehi-mcp
4. jawafdehi-mcp reads `X-Jawafdehi-User-Id`, calls `GET /api/caseworker/me` with the service account token
5. jawafdehi-api resolves the OpenWebUI user ID to a real Django user and returns roles
6. jawafdehi-mcp filters tools based on roles (caseworker → all tools, public → read-only)

## ChatUserIdentity Mapping

Before users can access caseworker tools, create `ChatUserIdentity` records
mapping OpenWebUI user IDs to Django users:

```python
from cases.models import ChatUserIdentity
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username="caseworker.name")
ChatUserIdentity.objects.create(owui_user_id="abc123-def456", user=user)
```

## Security

- jawafdehi-mcp port is internal only (`expose`, not `ports`) — unreachable from outside
- OpenWebUI's Custom Headers are the sole source of `X-Jawafdehi-*` headers
- Service account token is never exposed to end users
- jawafdehi-api enforces authorization server-side regardless of tool requests
