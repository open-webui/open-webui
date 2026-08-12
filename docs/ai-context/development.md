# Development and Validation

## Prerequisites and setup

The manifests are authoritative:

- Node.js: `package.json` currently allows `>=18.13.0 <=22.x.x`; upstream development documentation recommends a current Node 22 release.
- Python: `pyproject.toml` requires Python `>=3.11,<3.13`.
- Frontend packages use npm and are locked by `package-lock.json`.
- Python dependencies are locked in `uv.lock`; repository scripts and CI also use the requirements files under `backend/` in some environments.

Follow the [official source-development guide](https://docs.openwebui.com/getting-started/advanced-topics/development/) for initial environment setup, but resolve discrepancies in favor of the checked-out manifests and scripts.

Typical development uses two terminals:

```sh
# frontend, from the repository root
npm run dev

# backend, with the Python environment activated
cd backend
./dev.sh
```

The frontend normally proxies or calls the backend through the configured WebUI base URL. `backend/dev.sh` sets development CORS origins and starts `open_webui.main:app` with reload.

Do not use the real `.env` as documentation or copy values from it. Add safe placeholders to `.env.example` when introducing user-facing environment configuration.

## Common commands

Frontend commands from `package.json`:

| Purpose            | Command                 | Notes                                                                     |
| ------------------ | ----------------------- | ------------------------------------------------------------------------- |
| Development        | `nvm exec npm run dev`           | Fetches/prepares Pyodide, then starts Vite                                |
| Type/Svelte checks | `nvm exec npm run check`         | Runs SvelteKit sync and `svelte-check`                                    |
| Unit tests         | `nvm exec npm run test:frontend` | Runs Vitest                                                               |
| Production build   | `nvm exec npm run build`         | Produces the static SPA in `build/`                                       |
| Lint bundle        | `nvm exec npm run lint`          | Includes rewriting frontend lint; do not use casually on a dirty tree     |
| Format bundle      | `nvm exec npm run format`        | Rewrites broad globs; prefer targeted Prettier invocations                |
| i18n extraction    | `nvm exec npm run i18n:parse`    | Rewrites locale catalogs; run only for deliberate translation-key changes |

Backend checks reflected in `pyproject.toml` and CI:

```sh
ruff format --check backend/open_webui/path/to_changed.py
ruff check backend/open_webui/path/to_changed.py
pytest path/to/relevant_test.py
```

CI's backend undefined-name check uses a narrower Ruff selection and ignore list in `.github/workflows/backend.yaml`; CI's frontend workflow also checks formatting/i18n-generated diffs and runs the build and frontend tests. Inspect those workflows before claiming CI parity.

The current checkout has limited visible automated test coverage. Add focused tests for new pure logic and regressions rather than assuming a broad suite covers the touched subsystem.

## Validation by change type

### Frontend UI or state

- Run targeted Prettier check on changed `.svelte`/TypeScript files.
- Run `npm run check`.
- Run `npm run test:frontend` when logic is covered or tests were added.
- Run `npm run build` for routing, dependency, worker, or production-only changes.
- Manually check loading, empty, error, mobile, keyboard, and dark/light states when applicable.

### Frontend API client or chat behavior

- Validate request URL, method, credentials, authorization, payload omission/default behavior, abort/cancellation, and error parsing.
- Trace the backend endpoint and streaming/event consumer; do not validate only one side.
- Exercise temporary and persisted chats plus single- and multi-model behavior if relevant.

### Backend router or model

- Run targeted Ruff format and lint checks.
- Exercise authentication, admin/owner/grant boundaries, not-found behavior, validation errors, and response shape.
- For async persistence, use the async session helpers in `backend/open_webui/internal/db.py`; avoid introducing independent session conventions.

### Database schema or persisted representation

- Update the SQLAlchemy model and add a new migration under `backend/open_webui/migrations/versions/`.
- Verify upgrade from the previous schema with both default SQLite and the production database mode relevant to the deployment.
- Check indexes, nullability, default/backfill behavior, rollback expectations, and dual-write/read compatibility.
- Never rewrite an already-released migration to change existing installations.

### Retrieval, tool, or extension execution

- Test malformed and untrusted inputs, timeouts, authorization, secret handling, cancellation, and cleanup.
- For retrieval, test ingestion, retrieval, citations, resource deletion, and access isolation.
- For tools/MCP, test schema conversion, user-specific credentials/valves, tool errors, and iteration limits.

### Documentation only

- Confirm every referenced path and command exists.
- Check relative Markdown links.
- Run `git diff --check`.
- Do not run application builds unless documentation generation or packaged assets changed.

## Migrations and runtime data

Alembic configuration is under `backend/open_webui/`. Before creating or running migrations, inspect `backend/open_webui/migrations/README`, `backend/open_webui/migrations/env.py`, current heads, and the startup migration behavior controlled by `ENABLE_DB_MIGRATIONS`.

Treat these as runtime/generated data unless a task explicitly targets them:

- `build/`, `.svelte-kit/`, caches, coverage output, and downloaded Pyodide artifacts
- `backend/data/` and configured `DATA_DIR` contents
- SQLite/vector database files, uploads, generated media, audit logs, and secret-key files

Do not commit generated output unless the packaging/release workflow explicitly requires it.

## Docker and production checks

`docker-compose.yaml` starts Ollama and Open WebUI with named volumes. The `Dockerfile` has multiple image concerns/variants; read the complete file before changing build stages. `backend/start.sh` handles secret-key setup, optional bundled services, worker count, and final Uvicorn launch.

For deployment changes, verify:

- health/startup and graceful shutdown;
- persistence across container recreation;
- stable `WEBUI_SECRET_KEY` and session/OAuth/MCP token continuity;
- reverse-proxy origin, forwarded headers, and WebSocket support;
- multi-worker shared database, Redis/session state, and storage requirements;
- database migration ordering and rollback/backup procedure.

## Clean handoff

Before completion:

1. Re-run `git status --short` and distinguish your files from pre-existing changes.
2. Inspect `git diff --check` and the scoped diff.
3. State which checks passed, which were skipped, and why.
4. Call out migrations, deployment actions, manual verification, or follow-up decisions still required.
