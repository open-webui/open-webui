# Project Context Export

**Generated**: 2026-02-05  
**Purpose**: Export all relevant context for continuing work on this project.

---

## 1. Project Overview

**Name**: DSL KidsGPT Open WebUI  
**Repository**: https://github.com/jjdrisco/DSL-kidsgpt-open-webui  
**Base**: Open WebUI fork for research study (children + AI interactions)

**Stack**:
- Frontend: SvelteKit (adapter-static → `build/`)
- Backend: FastAPI + Uvicorn
- Database: SQLite (dev) / PostgreSQL (Heroku)
- Vector DB: pgvector (chromadb removed for Heroku slug size)

**Key Features**:
- Moderation workflow (parents review AI responses)
- Child profiles with personality-based scenarios
- Initial/exit surveys, workflow management
- Parent and child roles

---

## 2. Heroku Deployment Summary

### Deployment Paths

| Stack | Apps | Key Files |
|-------|------|-----------|
| **Container (Docker)** | contextquiz-openwebui-kidsgpt | Dockerfile, heroku.yml |
| **Buildpack** | dsl-kidsgpt-pilot | Procfile, app.json, requirements.txt (root) |

### Buildpack Requirement

**Node.js MUST be before Python** so frontend is built:
```bash
heroku buildpacks:add --index 1 heroku/nodejs -a YOUR_APP
heroku buildpacks:add heroku/python -a YOUR_APP
heroku config:set NPM_CONFIG_PRODUCTION=false -a YOUR_APP
```

### Current Blocker: Node.js OOM During Build

**Symptom**: `FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory` during `npm run build` on Heroku.

**Cause**: `npm run build` runs (1) `pyodide:fetch` (loads Pyodide/Python in Node – very memory-heavy) and (2) `vite build` (900+ modules). Combined, they exceed Node’s default heap (~1.5–2GB).

**Fix**: Set `NODE_OPTIONS="--max-old-space-size=4096"` on Heroku:
```bash
heroku config:set NODE_OPTIONS="--max-old-space-size=4096" -a dsl-kidsgpt-pilot
```
Then redeploy: `git push heroku main`

**Alternative**: If config var doesn’t work, add to `package.json` build script:
```json
"build": "NODE_OPTIONS=--max-old-space-size=4096 npm run pyodide:fetch && NODE_OPTIONS=--max-old-space-size=4096 vite build"
```

---

## 3. Critical Fixes Applied (2026-02)

### Backend
1. **azure.identity**: `backend/open_webui/routers/openai.py` – lazy import (was top-level, caused ModuleNotFoundError)
2. **Optional packages**: boto3, azure-*, firecrawl, ddgs, tencent, opentelemetry removed; lazy imports in code
3. **Procfile**: Release phase for Alembic migrations
4. **Migration 38d63c18f30f**: Conditional primary key on user table (fixes InvalidTableDefinition)

### Frontend
5. **Vite 7 package resolution**: Packages with only `svelte`/`types` in exports fail. **Fix**: Aliases in `vite.config.ts`:
   - svelte-confetti → dist/index.js
   - paneforge → dist/index.js
   - bits-ui → dist/index.js
   - @melt-ui/svelte → dist/index.js
6. **npm lockfile sync**: Regenerated lockfile; `engines.npm: "10.x"` to match Node 20.x
7. **engines.node**: `"20.x"` (was wide range causing npm 21; dependency required 20.17+ or 22.9+)
8. **xlsx → exceljs**: Replaced vulnerable xlsx with exceljs + papaparse in `FileItemModal.svelte`

### Deployment
9. **404 fix**: Add nodejs buildpack before python (frontend not built otherwise)
10. **CORS**: Use explicit origins, not `*`
11. **heroku.yml**: `cd backend/open_webui` for release (was `cd open_webui`)

---

## 4. Key Files and Directories

| Path | Purpose |
|------|---------|
| `vite.config.ts` | resolve.conditions + aliases for svelte-confetti, paneforge, bits-ui, @melt-ui/svelte |
| `package.json` | engines: node 20.x, npm 10.x; build script |
| `src/lib/components/common/FileItemModal.svelte` | Excel/CSV preview (exceljs, papaparse) |
| `backend/open_webui/main.py` | FastAPI app, SPA mount, CORS |
| `backend/open_webui/config.py` | VECTOR_DB=pgvector, STORAGE_PROVIDER, ENABLE_OTEL |
| `backend/open_webui/storage/provider.py` | Lazy imports for S3, GCS, Azure |
| `backend/open_webui/routers/openai.py` | Lazy azure.identity |
| `Procfile` | Release (alembic) + web (uvicorn) |
| `heroku.yml` | Docker build/release/run |
| `requirements.txt` (root) | Slimmed for Heroku |
| `.slugignore` | Excludes from buildpack slug |
| `scripts/prepare-pyodide.js` | Pyodide fetch (memory-heavy) |

---

## 5. Documentation Index

| Document | Location | Use |
|----------|----------|-----|
| **Deployment Agent Prompt** | `DEPLOYMENT_AGENT_PROMPT.md` | Prompt for cloud agent to fix deployment |
| Heroku Deployment | `docs/HEROKU_DEPLOYMENT.md` | Full Heroku guide + troubleshooting |
| Heroku 404 Fix | `docs/HEROKU_404_FIX.md` | Fix 404 on / |
| Heroku Backup | `docs/HEROKU_BACKUP_SETUP.md` | Postgres backup |
| Deployment Summary | `deployment-summary.txt` | High-level deploy summary |
| Project Continuation Guide | `docs/PROJECT_CONTINUATION_GUIDE.md` | Main project overview |

---

## 6. Environment / Config Reference

### Heroku Config Vars (Build – OOM Fix)

```
NODE_OPTIONS=--max-old-space-size=4096
NPM_CONFIG_PRODUCTION=false
```

### Heroku Config Vars (Runtime)

```
CORS_ALLOW_ORIGIN=https://yourapp.herokuapp.com;http://localhost:8080
VECTOR_DB=pgvector
WEB_CONCURRENCY=1
MALLOC_ARENA_MAX=2
ENABLE_IMAGE_GENERATION=false
AUDIO_STT_ENGINE=""
AUDIO_TTS_ENGINE=""
ENABLE_RAG_WEB_SEARCH=false
ENABLE_RAG_LOCAL_WEB_FETCH=false
```

### Database Migrations

```bash
cd backend/open_webui && alembic upgrade head
```

---

## 7. Debugging Quick Reference

| Symptom | Fix |
|---------|-----|
| **Node OOM during build** | Set `NODE_OPTIONS=--max-old-space-size=4096` on Heroku |
| 404 on /, /parents | Add nodejs buildpack before python |
| `npm ci` "Missing from lock file" | Regenerate lockfile, pin engines.npm 10.x |
| svelte-confetti/paneforge/bits-ui resolve fail | Aliases in vite.config.ts (already applied) |
| ModuleNotFoundError: azure | Ensure routers/openai.py has lazy import |
| Slug too large | Check .slugignore, requirements.txt |
| R14 Memory (runtime) | WEB_CONCURRENCY=1, lazy imports |
| Migration fails | Check Procfile release phase, migration 38d63c18f30f |

---

## 8. Local Build Verification

```bash
npm run build   # Must succeed locally before deploy
```

If local build succeeds but Heroku fails with OOM, apply the NODE_OPTIONS config var.
