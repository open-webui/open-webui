# Architecture

## System shape

Open WebUI is a browser application and Python API packaged as one production service:

- The frontend is a SvelteKit 2 application using Svelte 5, TypeScript, Vite, and Tailwind. Routes live in `src/routes/`, reusable UI in `src/lib/components/`, API clients in `src/lib/apis/`, and shared stores/types in `src/lib/stores/`.
- The backend is a FastAPI application rooted at `backend/open_webui/main.py`. Feature routers live in `backend/open_webui/routers/`, persistence models in `backend/open_webui/models/`, and cross-cutting behavior in `backend/open_webui/utils/`.
- Development normally runs Vite and Uvicorn separately. Production builds the static SvelteKit SPA into `build/`; the Python package includes it as `open_webui/frontend`, and FastAPI serves it through `SPAStaticFiles` after API/static mounts.
- Browser real-time traffic uses Socket.IO. The client connection is initialized in `src/routes/+layout.svelte` with path `/ws/socket.io`; `backend/open_webui/main.py` mounts the Socket.IO ASGI app from `backend/open_webui/socket/main.py` at `/ws`.

The root layout initializes configuration, authentication, localization, connection state, and global stores. The `(app)` layout loads authenticated application data such as models, tools, banners, terminal servers, and user settings.

## Backend composition

`backend/open_webui/main.py` is the composition root:

- `lifespan` initializes and tears down runtime services.
- `app = FastAPI(...)` configures middleware, exception handling, and application state.
- Feature routers are registered under `/api/v1/*`; provider compatibility routers are mounted under `/ollama` and `/openai`.
- App-level compatibility and orchestration endpoints include `/api/models` and `/api/chat/completions`.
- `/static`, optional `/pyodide`, and finally the SPA fallback are mounted after API routes.

Authentication schemas and credential persistence are in `backend/open_webui/models/auths.py`; endpoint behavior is in `backend/open_webui/routers/auths.py`; request authentication helpers are in `backend/open_webui/utils/auth.py`. Authorization is not just role-based: resources can also use groups, ownership, permissions, and grants. Inspect `backend/open_webui/models/access_grants.py` and resource-specific access helpers before changing visibility or sharing.

## Chat request and streaming flow

The primary persisted-chat path is:

1. `src/lib/components/chat/Chat.svelte` owns chat composition. `submitPrompt` adds a user message to the local message tree; `sendMessage` creates one or more assistant placeholders; `sendMessageSocket` assembles model, feature, file, tool, skill, terminal, session, chat, and message metadata.
2. `generateOpenAIChatCompletion` in `src/lib/apis/openai/index.ts` posts JSON to `/api/chat/completions`. Despite its name, this is the WebUI orchestration endpoint, not necessarily a direct OpenAI provider call.
3. `chat_completion` in `backend/open_webui/main.py` authenticates and normalizes the request, resolves the selected model(s), creates a new chat when necessary, verifies ownership for an existing chat, and persists user/assistant placeholder state.
4. `process_chat_payload` in `backend/open_webui/utils/middleware.py` applies model parameters, filters, tools, files/RAG context, knowledge, memory, system prompts, and other feature metadata.
5. `generate_chat_completion` in `backend/open_webui/utils/chat.py` routes to a Function/Pipe, Ollama, or an OpenAI-compatible provider. Provider adapters are primarily `backend/open_webui/routers/ollama.py` and `backend/open_webui/routers/openai.py`.
6. `process_chat_response` in `backend/open_webui/utils/middleware.py` consumes streaming/non-streaming output, performs tool/code-interpreter continuation loops, emits events, records usage/errors, and finalizes message state.
7. Socket helpers broadcast status and completion events to the user/session rooms. `Chat.svelte` reconciles those events into the local message tree and UI.

Temporary chats are an exception: the browser includes conversation messages because there is no normal persisted server history. Persisted chats rely on server-side history and identifiers. Multi-model chat uses `message_ids` entries (including `modelIdx`) so parallel or duplicate-model responses remain distinct.

When editing this flow, preserve identifiers (`chat_id`, message IDs, parent/child relationships, session ID), stream semantics, event payloads, cancellation, error finalization, and side-by-side model behavior.

## Chat persistence

`backend/open_webui/models/chats.py` defines the `chat` table and `ChatsTable`. A chat stores top-level metadata plus a legacy JSON representation of the conversation. `backend/open_webui/models/chat_messages.py` defines the normalized `chat_message` table.

Message writes use methods such as `Chats.upsert_message_to_chat_by_id_and_message_id`; the implementation updates legacy history and writes normalized message records. `Chats.insert_new_chat` also dual-writes initial messages. This compatibility behavior is intentional: do not remove either representation or bypass the table methods without a dedicated migration and compatibility plan.

`backend/open_webui/models/messages.py` is a different `message` table used for channel messaging. Do not confuse channel messages with chat-completion messages.

## Data and configuration

- `backend/open_webui/env.py` reads process environment and establishes paths such as `DATA_DIR` and `DATABASE_URL`.
- `backend/open_webui/config.py` defines runtime settings, including database-persisted configuration.
- `backend/open_webui/internal/db.py` creates synchronous startup and asynchronous runtime SQLAlchemy engines/sessions. SQLite is the default; PostgreSQL and other configured database modes are supported.
- Schema history lives in `backend/open_webui/migrations/versions/` and is managed by Alembic using `backend/open_webui/alembic.ini`.
- Uploaded files, caches, local database files, and vector data live below `DATA_DIR` by default and are runtime data, not source assets.

Many settings are persistent `ConfigVar` values. With `ENABLE_PERSISTENT_CONFIG=true` (the default), a value saved in the database can take precedence over a later environment-variable change. Admin UI changes and startup behavior must be analyzed with that precedence in mind. See the [official configuration reference](https://docs.openwebui.com/reference/env-configuration/) and verify the actual definition in `config.py`.

Never inspect or expose `.env` while gathering configuration examples. Use `.env.example`, `env.py`, and `config.py`.

## Retrieval, files, and knowledge

Retrieval APIs are composed through `backend/open_webui/routers/retrieval.py` and `backend/open_webui/routers/knowledge.py`. Loaders, embedding/reranking integrations, web search engines, and vector backends live under `backend/open_webui/retrieval/`; vector selection is coordinated by `backend/open_webui/retrieval/vector/factory.py` and configuration such as `VECTOR_DB`.

The chat middleware converts selected files, collections, folders, notes, and knowledge into sources/context before provider dispatch. Any retrieval change should be checked at both ingestion and chat-time retrieval, including access control, citations/source metadata, deletion, and vector-store cleanup.

## Extensibility surfaces

These terms have distinct meanings in this codebase:

- **Tools** give models callable capabilities. Records and API behavior are in `backend/open_webui/models/tools.py` and `backend/open_webui/routers/tools.py`; execution/normalization is in `backend/open_webui/utils/tools.py`.
- **Functions** are database-backed Python extensions loaded dynamically by `backend/open_webui/functions.py`, with management in the corresponding model/router. Pipe, Filter, Action, and Event classes extend platform/model behavior.
- **Skills** are reusable instruction/content resources managed by `backend/open_webui/models/skills.py` and `backend/open_webui/routers/skills.py` and injected into chat context when selected or mentioned.
- **MCP and OpenAPI tool servers** are external tool surfaces. MCP transport is implemented in `backend/open_webui/utils/mcp/client.py`; server discovery and tool exposure pass through the tools router/utilities.
- **Pipelines** remain for compatibility in `backend/open_webui/routers/pipelines.py`, but official guidance treats external Pipelines as legacy for new deployments; prefer in-process Functions where they meet the requirement.

Tools, Functions, Pipes, Filters, Pipelines, and MCP servers can execute code or reach external systems with server/user authority. Follow the [official extension security warning](https://docs.openwebui.com/features/extensibility/plugin/): keep trust decisions explicit and preserve authentication, per-user valves/tokens, grant checks, secret redaction, timeouts, and network boundaries.

## Build and deployment

- `package.json`, `svelte.config.js`, and `vite.config.ts` define the frontend build. The SvelteKit static adapter emits `build/` with an SPA fallback.
- `pyproject.toml` defines the Python package and includes `build/` as `open_webui/frontend` in the wheel.
- `hatch_build.py` participates in packaging.
- `Dockerfile`, `backend/start.sh`, and `docker-compose*.yaml` define supported container variants and startup.
- `backend/dev.sh` runs the reload-enabled Uvicorn development server, normally on port 8080; Vite runs the browser development server.

Production deployments must persist `DATA_DIR`, use a stable `WEBUI_SECRET_KEY`, support WebSockets, and coordinate shared database/cache/storage settings when scaling beyond one worker. Confirm current requirements in source and the [official deployment documentation](https://docs.openwebui.com/getting-started/).
