# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

A **fork of [Open WebUI](https://github.com/open-webui/open-webui)** (`origin` =
`git@github.com:volkmen/open-webui.git`, upstream base ≈ v0.9.6), specialised into a
**document library / knowledge-base product**.

Upstream is a general LLM chat front-end. Our fork's own work — everything after
`02dc3e689 Merge pull request #25590 from open-webui/dev` — is almost entirely in the
**knowledge** domain:

- folder (directory) trees inside a knowledge base, preserved from folder uploads
- a **sequential file-processing queue** (`In queue` → `Processing` → done) instead of
  fire-and-forget ingestion
- presigned S3/MinIO direct upload
- AI-generated descriptions per file, rolled up per folder, then per knowledge base
  (`ai_overwiew` — note the upstream-style typo is the real column name)
- an embedding allowlist: only allowlisted document types are embedded, but **all**
  files still contribute AI context
- KB stats (file/folder counts, total size) with a client-side
  `statistics_outdated` flag instead of refetching
- extra catalog fields on a KB: `registration_number`, `registration_date`

**When touching `knowledge`, `files`, or `retrieval`, assume the code is ours and
diverges from upstream.** Elsewhere (chat, channels, audio, images, ollama, openai,
admin settings) assume it is upstream code — keep changes minimal and in upstream's
style so future merges stay cheap.

## Stack

| Layer     | Tech                                                                      |
| --------- | ------------------------------------------------------------------------- |
| Backend   | Python 3.11–3.12, FastAPI, SQLAlchemy 2.0 **async** (+ sync engine for Alembic), Alembic, Redis, Socket.IO |
| Frontend  | SvelteKit 2 / **Svelte 5**, TypeScript, Tailwind 4, Vite 5                 |
| Storage   | Local FS / S3 / MinIO via `open_webui.storage.provider.Storage`            |
| Vector DB | Chroma / Weaviate / OpenSearch / … via `ASYNC_VECTOR_DB_CLIENT`            |
| DB        | SQLite (dev/test) or PostgreSQL (psycopg3 async, psycopg2 for migrations)  |

## Testing is mandatory

**Every change ships with tests, and every feature is covered end-to-end by an
integration test.** See [`docs/architecture/testing.md`](docs/architecture/testing.md)
for the harness, the mock boundaries, and the traps.

- A new/changed feature needs an integration test that hits the **real HTTP endpoint
  against a real (temp SQLite) DB**, mocking only external boundaries (LLM, S3).
- A new pure function needs a unit test. Hard to test = wrong layer; extract it.
- A bug fix starts with a failing test.
- Keep at least one full-stack test per pipeline with **nothing** mocked.

If you genuinely cannot cover something, say so explicitly — don't ship silently
uncovered code.

CI runs `pytest` (backend.yaml) and `vitest` (frontend.yaml). Note the path filters: a
frontend-only change does **not** trigger pytest, and vice versa — so run both locally.
`--passWithNoTests` means a green frontend run is not evidence of coverage.

## Commands

```bash
# Backend (from backend/) — loads backend/.lde.env, creates the MinIO bucket, runs uvicorn --reload
./dev.sh

# Frontend
npm run dev                 # vite dev --host (fetches pyodide first)
npm run build

# Tests
pytest                      # backend; testpaths=backend/tests, asyncio_mode=auto
pytest backend/tests/test_knowledge_delete.py -k folder
npm run test:frontend       # vitest (--passWithNoTests)

# Lint / format
npm run lint                # eslint + svelte-check + pylint backend/
npm run check               # svelte-check only (type errors)
npm run format              # prettier
npm run format:backend      # ruff format
```

There is a pre-commit hook running `ruff --fix backend` and `ruff-format backend`.

## Code style (enforced — don't fight it)

- **Python**: ruff, line length **120**, **single quotes**, isort-ordered imports,
  `mccabe.max-complexity = 10`. Google-style docstrings. `datetime` must be imported
  as `dt`; `ast` and bare `datetime` imports are banned.
- **Svelte/TS**: prettier with **tabs**, **single quotes**, `printWidth: 100`,
  no trailing commas.
- The complexity cap of 10 is the mechanical reason most new endpoint logic belongs
  in a service rather than in the router body.

## Layout

```
backend/open_webui/
  main.py               # FastAPI app, router registration (~line 1419+), lifespan, workers
  config.py             # persisted app config (huge; DB-backed settings)
  env.py                # env-var only settings, read at import time
  internal/db.py        # Base, engines, get_async_session (FastAPI dep), get_async_db_context
  routers/              # HTTP layer — one module per domain, mounted at /api/v1/<name>
  services/             # NEW: orchestration (files_service, file_analysis, process_file_queue)
  models/               # SQLAlchemy tables + Pydantic schemas + *Table repository classes
  utils/                # cross-cutting: auth, access_control, middleware, chat, misc
  retrieval/            # loaders, vector clients, web search
  storage/provider.py   # file storage abstraction
  migrations/           # Alembic
  tests/ (backend/tests) # pytest + httpx ASGI integration tests

src/                     # SvelteKit frontend
  routes/               # pages; (app) group = authenticated shell
  lib/apis/<domain>/    # thin fetch wrappers, one dir per backend router
  lib/components/       # Svelte components (see docs/architecture/frontend-components.md)
  lib/stores/index.ts   # global writable stores
  lib/utils/            # pure helpers — the right home for extracted component logic
  lib/i18n/             # i18next; run `npm run i18n:parse` after adding strings
```

## Backend patterns you must follow

**Auth + DB session come from FastAPI dependencies:**

```python
@router.post('/{id}/update', response_model=KnowledgeResponse | None)
async def update_knowledge_by_id(
    id: str,
    form_data: KnowledgeForm,
    user=Depends(get_verified_user),          # or get_admin_user
    db: AsyncSession = Depends(get_async_session),
):
```

**Repositories take an optional `db` and open their own session if not given** —
always thread `db=db` through so one request is one transaction:

```python
async def get_knowledge_by_id(self, id: str, db: Optional[AsyncSession] = None):
    async with get_async_db_context(db) as db:
        ...
```

**Each `models/*.py` ends with a module-level singleton** — that is the repository
handle everything imports:

```python
Knowledges = KnowledgeTable()
Files = FilesTable()
Users = UsersTable()
```

**Authorisation is explicit, never implicit.** Ownership check *plus*
`AccessGrants.has_access(...)` *plus* an `user.role != 'admin'` escape hatch, and
`has_access_to_file` for per-file reads. Copy the shape from a neighbouring endpoint
in the same router; never invent a new gate.

**Errors**: raise `HTTPException` with a message from `open_webui.constants.ERROR_MESSAGES`.

## Architecture direction (read before adding a feature)

The current backend is **two layers**: fat routers calling `models/` classes that are
already repositories in all but name. We are moving to **routers → services →
repositories**, and the frontend from monolithic components to composed ones.

**This is opportunistic, not a big-bang refactor.** Do not go refactor working code
you were not asked to touch. Do apply the target shape to anything new, and to code
you are already modifying substantially.

Full rules, with worked examples from this codebase:

- [`docs/architecture/backend-layers.md`](docs/architecture/backend-layers.md) —
  routers / services / repositories
- [`docs/architecture/frontend-components.md`](docs/architecture/frontend-components.md) —
  splitting and reusing Svelte components
- [`docs/architecture/testing.md`](docs/architecture/testing.md) —
  coverage policy, integration-test harness, mock boundaries

Testability is the main reason for the layering: logic inside a 120-line router body can
only be reached over HTTP, while the same logic in a service is directly callable — a
service test is the end-to-end feature test minus the HTTP hop.

Short version:

| Layer            | Home                | May do                                                          | May **not** do                              |
| ---------------- | ------------------- | --------------------------------------------------------------- | ------------------------------------------- |
| **Router**       | `routers/*.py`      | parse/validate input, resolve `user` + `db`, authorise, call one service, map errors to HTTP | multi-step business logic, direct `select()` |
| **Service**      | `services/*.py`     | orchestrate repositories, storage, vector DB, LLM calls, queues  | touch `Request`/`HTTPException`, emit SQL   |
| **Repository**   | `models/*.py`       | SQL for its own aggregate, row ↔ Pydantic mapping                | LLM/storage/HTTP calls, cross-domain policy |

## Traps in this codebase

- `main.py`, `config.py` and `utils/middleware.py` are 3k–5k lines. Adding to them is
  almost always wrong — add a router or service instead.
- `ai_overwiew` is spelled that way in the DB. Don't "fix" it without a migration.
- `services/file_analysis.py` is **fail-open** by design: an LLM or parse failure must
  return "eligible" so a classifier outage never silently drops uploads. Preserve that.
- `backend/dev.sh` passes `--reload-dir open_webui --reload-exclude 'data/*'` on purpose —
  without it, uploading a `.py` file restarts the server mid-request.
- `backend/tests/conftest.py` *forces* `DATABASE_URL` to a temp SQLite file before any
  `open_webui` import. Never import `open_webui` above that block.
- Frontend API wrappers swallow the error into a local `error` var and then `throw error`.
  Match that shape; callers expect a thrown detail string, not a `Response`.
- Adding a UI string means adding it to `src/lib/i18n` and running `npm run i18n:parse`.

## Git conventions

Conventional commits, scoped by domain — the fork's history is consistent:

```
feat(knowledge): embed only allowlisted document types; keep AI context for all
test(knowledge): extract withStatsOutdated util + vitest tests
perf(knowledge): remove deleted file/folder locally instead of refetching
```

Branch names look like `feature/knowledge-migration`. Only commit or push when asked.
