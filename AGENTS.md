## Docker-only local workflow (mandatory)

**Run this application only via Docker.** Do not start the stack or “do local dev” with bare `python`, `pip`, `uv`, `uvicorn`, `npm`, or `node` on the host machine for this project.

- **Do not** create a host `venv`, **do not** run `pip install` / `uv pip install` on the host for app or test runs, and **do not** run `npm install` or maintain a host `node_modules` for running the app or tests.
- **Do** run the app and installs **inside** containers built from this repo’s Docker setup. If the user explicitly asks you to run or add tests, run them inside Docker too (see below)—**do not** create or run tests on your own initiative.

**Compose file:** Use **only** `docker-compose.local.yaml` for local Docker workflows. Do not use `docker-compose.yaml`, `docker-compose.yml`, or other compose files for local development unless a human explicitly directs otherwise (those are for production/CI patterns).

```bash
docker compose -f docker-compose.local.yaml up              # Start
docker compose -f docker-compose.local.yaml up --build        # Rebuild and start
docker compose -f docker-compose.local.yaml down              # Stop
```

The `develop.watch` section in `docker-compose.local.yaml` syncs `./backend` and `./src` into the running container; dependency changes trigger an image rebuild—still **via this compose file**, not host package managers.

### Tests (user permission)

**Do not** create new tests, **do not** run the test suite, and **do not** add test files or scaffolding unless the user explicitly tells you to. When they do, follow the Docker-only commands below.

### Running tests (inside Docker, only when asked)

When the user has asked you to run tests, run them by **exec’ing or running a one-off command in a service container**—never by provisioning a host venv or `node_modules` for that purpose.

Examples (adjust paths if your shell’s cwd inside the container differs; backend workdir is typically `/app/backend`):

```bash
# After the stack is up:
docker compose -f docker-compose.local.yaml exec open-webui pytest open_webui/test/

# One-off container (no daemon) if you only need tests:
docker compose -f docker-compose.local.yaml run --rm open-webui pytest open_webui/test/
```

Frontend or other Node-based test commands, if needed, must also be executed **inside** an appropriate container image for this project—not via host `npm`.

### Reference only (not host commands)

The following are **conceptual** equivalents for what happens **inside Docker or in image build stages** (multi-stage `Dockerfile` uses `npm ci` / `npm run build` and `uv pip install` from `requirements.txt`). **Do not** treat these as instructions to run on the developer machine:

- Frontend: SvelteKit + Vite — `npm run build`, `npm run test:frontend`, lint/format as defined in `package.json`
- Backend: FastAPI — dependencies from `backend/requirements.txt`, `pytest` for `backend/open_webui/test/`

## Project Overview

NAGA is a fork of [Open WebUI](https://github.com/open-webui/open-webui) (v0.5.14), customized by NYU-ITS as a self-hosted AI platform. It adds NYU-specific features including a grant-writing assistant (`facilities` router), async file processing via Redis Queue, and OpenTelemetry integration for OpenShift Observe.

## Architecture

This is a monorepo: SvelteKit SPA frontend + FastAPI backend. The frontend builds to static files served by the Python app (built in Docker).

### Frontend (`src/`)
- `src/routes/` — SvelteKit file-based routing (chat, admin, auth, workspace, channel pages)
- `src/lib/components/` — UI components organized by domain (chat, admin, workspace, common, layout)
- `src/lib/apis/` — One module per backend resource (auths, chats, models, ollama, openai, files, knowledge, retrieval, etc.)
- `src/lib/stores/` — Global Svelte stores
- `src/lib/i18n/` — i18next localization
- `src/lib/pyodide/` — Python-in-browser (Pyodide) for code execution

### Backend (`backend/open_webui/`)
- **Entry point:** `main.py` — assembles FastAPI app, mounts Socket.IO ASGI, registers all routers
- `routers/` — FastAPI route handlers, one file per resource. NAGA additions: `facilities.py` (NYU grant-writing RAG endpoint)
- `models/` — SQLAlchemy ORM models
- `retrieval/` — RAG subsystem:
  - `vector/connector.py` — selects active vector DB (ChromaDB default, pgvector, Milvus, Qdrant, OpenSearch)
  - `vector/dbs/` — Vector DB connector implementations
  - `loaders/` — Document loaders (PDF, DOCX, etc.)
  - `web/` — Web search backends (Tavily, Brave, Bing, DuckDuckGo, etc.)
- `workers/` — **NAGA custom:** RQ (Redis Queue) async file processor (`file_processor.py`). Enabled via `ENABLE_JOB_QUEUE=true`
- `socket/main.py` — Socket.IO server; supports Redis manager for horizontal scaling
- `storage/provider.py` — Pluggable file storage: Local, S3, GCS, Azure Blob
- `migrations/` — Alembic migrations (run automatically on startup)
- `config.py` — All configuration, driven entirely by environment variables
- `utils/` — Auth (JWT), audit logging, OpenTelemetry instrumentation

### Database
- **Primary DB:** SQLAlchemy ORM; SQLite by default, PostgreSQL in production (`DATABASE_URL` env var)
- **Vector DB:** ChromaDB by default; switched via `VECTOR_DB` env var
- **WebSocket/Queue state:** Redis (optional; required for RQ worker and horizontal Socket.IO scaling)

## NAGA-Specific Customizations

| Feature | Location | Activation |
|---|---|---|
| Grant-writing assistant | `routers/facilities.py` | Always on |
| Async file processing | `workers/file_processor.py` | `ENABLE_JOB_QUEUE=true` |
| OpenTelemetry | `utils/` + `main.py` | `OTEL_ENABLED=true` |
| NYU timezone | `main.py` | Hardcoded `America/New_York` |

## Key Setup Requirements

1. Copy `.env.example` to `.env` before starting — backend reads it automatically via `env.py` (when running in Docker as configured).
2. Pyodide and frontend assets are produced during the **Docker image build** (`npm run build` in the `Dockerfile`), not by a host `npm run dev`.
3. `docker-compose.local.yaml` expects PostgreSQL reachable where `DATABASE_URL` points (e.g. on the host — see `host.docker.internal` in that file).
4. The `facilities` router uses Tavily for web search — requires `TAVILY_API_KEY` in env when using that feature.
5. Python 3.13+ is explicitly unsupported (enforced in `pyproject.toml`).
