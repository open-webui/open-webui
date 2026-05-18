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
| `docker-compose.yml` | Reference stack (builds from `jawafdehi-main` source). Suitable for development. |
| `docker-compose.prod.yml` | Production deployment config (pre-built images, MCP, GCP Cloud Logging). Single-file stack. |
| `openwebui/tools-config.json` | OpenWebUI External Tools MCP server config |
| `mcp.env.example` | Template for jawafdehi-mcp environment variables |
| `.env.example` | Template for OpenWebUI OAUTH environment variables |
| `custom/` | Python overrides bind-mounted in production (middleware, tools) |
| `static/` | Jawafdehi branding assets (favicon, logo, splash screens) |
| `nginx/chat.jawafdehi.org.conf` | Nginx reverse proxy config (HTTP → HTTPS → OpenWebUI:8080) |
| `bin/deploy.sh` | Self-contained deploy script (run on monal host; pulls compose + custom files from repo) |

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

## Production Deployment (monal-instance1)

The production stack uses pre-built Docker Hub images, custom Python overrides,
and GCP Cloud Logging — all in a single `docker-compose.prod.yml`.

### Quick Deploy (from monal host)

```bash
cd /opt/openwebui && ./deploy.sh
```

This pulls the latest compose file, custom Python overrides, and static assets
from the `jawafdehi-main` branch, then pulls the latest Docker image and restarts.

### Manual Deploy

```bash
cp mcp.env.example mcp.env
cp .env.example .env
# Edit both with real credentials
docker compose -f docker-compose.prod.yml up -d
```

### GCP Cloud Logging

The gcplogs driver is baked into `docker-compose.prod.yml` (newnepal2 project).
Requires gcloud CLI authenticated on the host with
`owui-log-writer@newnepal2` service account credentials.

See [JAWA-1361](/JAWA/issues/JAWA-1361) for the investigation and implementation details.

## Security

- jawafdehi-mcp port is internal only (`expose`, not `ports`) — unreachable from outside
- OpenWebUI's Custom Headers are the sole source of `X-Jawafdehi-*` headers
- Service account token is never exposed to end users
- jawafdehi-api enforces authorization server-side regardless of tool requests
- Never commit `.env`, `mcp.env`, or GCP service account keys to the repository
