# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Open WebUI — a self-hosted AI platform: SvelteKit frontend + FastAPI backend, packaged as a single container that serves the built static frontend from the backend. Supports multiple LLM runners (Ollama, OpenAI-compatible APIs), RAG against 9 vector DB backends, web search, image generation, voice/STT/TTS, plugins, and a runtime extensibility model (Functions, Tools, Pipelines).

## Common commands

Frontend (Node `>=18.13 <=22`, npm):

- `npm run dev` — Vite dev server on `:5173` (auto-fetches Pyodide assets first via `scripts/prepare-pyodide.js`).
- `npm run build` — production build to `build/` (also runs `pyodide:fetch`).
- `npm run check` — `svelte-kit sync && svelte-check` against `tsconfig.json`. Use `check:watch` for watch mode.
- `npm run lint` — runs frontend ESLint, then `svelte-check`, then `pylint backend/`. Use `lint:frontend` / `lint:types` / `lint:backend` individually.
- `npm run format` — Prettier across `**/*.{js,ts,svelte,css,md,html,json}`. `format:backend` runs `ruff format`.
- `npm run test:frontend` — Vitest (currently `--passWithNoTests`).
- `npm run i18n:parse` — extract i18n keys from `src/**/*.{js,svelte}` into `src/lib/i18n/locales/$LOCALE/translation.json`.
- `npx cypress open` (or `npm run cy:open`) — interactive E2E. Specs live in `cypress/e2e/*.cy.ts` and assume `baseUrl=http://localhost:8080`, so run a backend that proxies the frontend (or the prod build) before opening.

Backend (Python 3.11–3.12, managed with `uv`/`hatch`; `pyproject.toml` is canonical, `requirements.txt` mirrors it):

- `cd backend && ./dev.sh` — uvicorn with `--reload`, listens on `:8080`, sets `CORS_ALLOW_ORIGIN` to allow the Vite dev server at `:5173`.
- `cd backend && ./start.sh` — production entrypoint (workers via `UVICORN_WORKERS`, generates `.webui_secret_key`, conditionally installs Playwright browsers, etc.). The Docker image runs this.
- `pytest backend/open_webui/test/...` — pytest+pytest-asyncio. Tests under `backend/open_webui/test/apps/webui/routers/` use `pytest-docker` to spin up Postgres; ensure Docker is available. Run a single test with the standard `pytest path::test_name` form.
- Pre-commit runs `ruff --fix backend` then `ruff format backend` (`.pre-commit-config.yaml`); ruff config (line length 120, single quotes, isort, mccabe ≤10) lives in `pyproject.toml`.

Docker / Compose:

- `make install` (= `docker compose up -d`) brings up `ollama` + `open-webui`. `make startAndBuild` rebuilds the image. `docker-compose.*.yaml` overlays add GPU/AMD/Playwright/OTel/etc. — combine with `-f`.
- The Dockerfile builds the frontend in a Node 22 stage (note `NODE_OPTIONS=--max-old-space-size=4096`) and copies `build/` into the Python backend image, which is then served by FastAPI's static files mount.

## Architecture

### Frontend (SvelteKit, Svelte 5)

- `svelte.config.js` uses `@sveltejs/adapter-static` with SPA fallback (`fallback: 'index.html'`) — output is a static bundle the FastAPI backend serves. The version field shells out to `git rev-parse HEAD` so deployed clients can detect new revisions and trigger a reload.
- `vite.config.ts` injects `APP_VERSION` / `APP_BUILD_HASH`, copies onnxruntime-web JSEP wasm into `build/wasm`, and strips `console.log/debug/error` outside `ENV=dev`.
- API base URLs come from `src/lib/constants.ts`: in dev the frontend hardcodes `http://${hostname}:8080` (so the FastAPI backend at 8080 must be running alongside `vite dev`); in prod it uses relative paths. `WEBUI_API_BASE_URL = `${WEBUI_BASE_URL}/api/v1`` is the canonical mount.
- Per-domain API clients are split under `src/lib/apis/<domain>/` and mirror the backend routers (chats, channels, files, models, ollama, openai, retrieval, tools, ...). Most state goes through the global stores barrel `src/lib/stores/index.ts`.
- Major in-browser features: a Pyodide worker for client-side Python (`src/lib/workers/pyodide.worker.ts`, `src/lib/pyodide/*`), a Kokoro TTS worker, TipTap-based rich text input, CodeMirror code editing, Mermaid/KaTeX/Vega rendering, and `socket.io-client` for live channels/events.
- Routes: marketing/auth pages at `src/routes/{auth,error,s,watch}` and the main app under `src/routes/(app)/`. Most chat UI is composed under `src/lib/components/chat/`.

### Backend (FastAPI, Starlette, SQLAlchemy 2.0)

- Entry point: `backend/open_webui/main.py`. The `lifespan` constructs the app, mounts the Socket.IO ASGI app from `open_webui/socket/main.py`, applies a stack of middlewares (`AuthTokenMiddleware`, `CommitSessionMiddleware`, `RedirectMiddleware`, `WebsocketUpgradeGuardMiddleware`, `AuditLoggingMiddleware`, Starlette + starsessions sessions, optional Redis-backed session store, compression, CORS), and includes ~30 routers from `open_webui/routers/*.py` under `/api/v1/`.
- Domain layout: each feature has parallel files in `routers/`, `models/`, and (where applicable) `utils/` — e.g. `routers/chats.py` ↔ `models/chats.py` ↔ `utils/chat.py`. Models use SQLAlchemy ORM and Pydantic schemas in the same file.
- Database: `open_webui/internal/db.py` builds both sync and async engines from `DATABASE_URL` (SQLite default, Postgres/MySQL/MariaDB supported). PostgreSQL SSL params are stripped/re-injected differently for asyncpg vs psycopg2 (`extract_ssl_mode_from_url`). Session helpers: `ScopedSession`, `get_async_session`, plus `peewee_migrate` for legacy migrations and Alembic for current ones (`open_webui/migrations/`, config in `alembic.ini`).
- Realtime: `open_webui/socket/main.py` runs Socket.IO over Redis (or in-memory) for multi-worker/multi-node deployments; co-edits notes with `pycrdt`. Background tasks scheduled via `APScheduler` and `open_webui/tasks.py`.
- Config: `open_webui/env.py` resolves environment + `.env`, exposes feature flags and DB/Redis tuning. `open_webui/config.py` re-exports many of these and adds DB-backed runtime config (read/written via the `/configs` router). Treat `env.py` as static-at-boot and `config.py` values as potentially user-editable at runtime.
- RAG: `open_webui/retrieval/` is split into `loaders/` (Tika, Docling, Datalab Marker, MinerU, Document Intelligence, Mistral OCR, Firecrawl, ...), `models/` (embedding/reranking model loaders), `vector/` (Chroma, PGVector, Qdrant, Milvus, Elasticsearch/OpenSearch, Pinecone, S3 Vector, Oracle 23ai), and `web/` (web-search providers). The active backends are picked dynamically from config.
- Plugin/extensibility surface: `utils/plugin.py` dynamically loads user-supplied Python for **Functions** (`models/functions.py`, `routers/functions.py`, top-level `functions.py`) and **Tools** (`models/tools.py`, `routers/tools.py`). `RestrictedPython` and frontmatter `requirements:` blocks are honored — be careful editing these paths, they execute untrusted code by design.
- LLM providers: dedicated routers/utils for `ollama`, `openai`, `anthropic` (in `utils/anthropic.py`), plus generic OpenAI-compatible "Pipelines" (`routers/pipelines.py`) and MCP integration (`utils/mcp/`).

### Coupling between frontend and backend

- The Hatch build (`pyproject.toml` `tool.hatch.build.targets.wheel`) force-includes `build/` (the Vite output) into the wheel as `open_webui/frontend`, so a published Python package ships the SPA. When changing the build/output layout, update `force-include` and `hatch_build.py`.
- API contract is implicit: every change to a `routers/*.py` endpoint should be reflected in the matching `src/lib/apis/<domain>/index.ts`. There are no generated client types — both sides hand-roll the shapes.
- Auth flows go through `utils/auth.py` (JWT + cookie sessions + optional OAuth/LDAP/SCIM/trusted-header SSO). The frontend reads `user`/`config` stores populated from `/api/v1/auths` and `/api/v1/configs` on bootstrap.

## Deployment (Swept)

Swept ships this fork to GCP Cloud Run via `.github/workflows/build-deploy.yaml`. Three envs in GCP project `production-472518` / region `us-central1`, mirroring the `swept-workbench` setup:

| Env | Cloud Run service | URL |
|---|---|---|
| production | `swept-chat` | https://chat.swept.ai |
| staging | `staging-swept-chat` | https://staging.chat.swept.ai |
| demo | `demo-swept-chat` | https://demo.chat.swept.ai |

Image: `us-central1-docker.pkg.dev/production-472518/chat-releases/open-webui`. Auth: Workload Identity Federation via the existing `swept-ai` GitHub org provider, impersonating `github-deploy@production-472518.iam.gserviceaccount.com`. Persistence: Cloud SQL `swept-chat-db` (one Postgres instance, three databases) + GCS buckets `swept-chat-uploads-{prod,staging,demo}` (native GCS storage backend, ADC). Secrets follow workbench's `STAGING_` / `DEMO_` prefix convention (prod = no prefix). Push to `main` auto-deploys staging; demo and prod require `workflow_dispatch` (prod additionally gated by the `production` GitHub Environment).

**Important — manual setup, not Terraform.** The Swept side of the infra (workbench *and* this fork) was provisioned by hand with `gcloud`, mirroring how `swept-workbench` was originally bootstrapped. Pioneer (`pioneer-insurance` project) uses Terraform and is a separate story. Do not introduce Terraform here — it would drift from the manual source of truth. The runbook lives at `DEPLOYMENT.md`; when changing infra, update the runbook *and* re-run the affected `gcloud` commands.

Currently `WORKBENCH_URL` is pinned to `https://workbench.swept.ai` for all three envs — once the staging/demo workbench domains are mapped, source the URL per env in the workflow (search for `TODO(WORKBENCH_URL)`).

## Conventions

- Python: ruff `single`-quoted, line length 120, mccabe complexity ≤10. `flake8-import-conventions` bans `import ast` and bare `import datetime` (use `import datetime as dt`). Black config is also present (line length 120) but ruff is the formatter the pre-commit hook runs.
- TS/Svelte: tabs, single quotes, no trailing commas, print width 100, LF endings (`.prettierrc`). ESLint extends `eslint:recommended`, `@typescript-eslint`, `svelte`, `cypress`, `prettier`.
- i18n: never edit files under `src/lib/i18n/locales/<code>/translation.json` by hand — add the key in source via `$i18n.t('...')` and run `npm run i18n:parse`.
- Pyodide assets: `npm run dev` and `npm run build` both depend on `pyodide:fetch`, which downloads wheels listed in `scripts/prepare-pyodide.js` into `static/pyodide/`. If you need a new Pyodide-side package, add it there.

## Notable workflows

- `.github/workflows/pr-approve-bot.yml`: a maintainer can comment `/approve` on a PR and (if they have write/admin/maintain access) a GitHub App auto-submits an approving review. Several upstream workflows in `.github/workflows/*.disabled` are intentionally off in this fork.
