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
```

### Critical Fixes Applied (2026-02)

1. **azure.identity**: `backend/open_webui/routers/openai.py` – lazy import (was top-level, caused ModuleNotFoundError)
2. **404 fix**: Add nodejs buildpack before python (frontend not built otherwise)
3. **Optional packages**: boto3, azure-*, firecrawl, ddgs, tencent, opentelemetry removed; lazy imports in code
4. **CORS**: Use explicit origins, not `*`
5. **Procfile**: Release phase for Alembic migrations
6. **Migration 38d63c18f30f**: Conditional primary key on user table (fixes InvalidTableDefinition)

### Optional Packages (Install If Needed)

See `requirements.txt` comments. Examples: boto3 (S3 storage), azure-identity (Azure OpenAI), firecrawl-py, ddgs, opentelemetry-*.

---

## 3. Key Files and Directories

| Path | Purpose |
|------|---------|
| `backend/open_webui/main.py` | FastAPI app, SPA mount, CORS |
| `backend/open_webui/config.py` | VECTOR_DB=pgvector, STORAGE_PROVIDER, ENABLE_OTEL |
| `backend/open_webui/env.py` | FRONTEND_BUILD_DIR, BASE_DIR, DATA_DIR |
| `backend/open_webui/storage/provider.py` | Lazy imports for S3, GCS, Azure |
| `backend/open_webui/retrieval/loaders/main.py` | Lazy Azure Document Intelligence |
| `backend/open_webui/retrieval/web/utils.py` | Lazy Firecrawl |
| `backend/open_webui/retrieval/web/duckduckgo.py` | Lazy DDGS |
| `backend/open_webui/retrieval/web/sougou.py` | Lazy Tencent |
| `backend/open_webui/utils/logger.py` | Conditional OpenTelemetry |
| `backend/open_webui/routers/openai.py` | Lazy azure.identity |
| `Procfile` | Release (alembic) + web (uvicorn) |
| `requirements.txt` (root) | Slimmed for Heroku |
| `backend/requirements.txt` | Full deps (Docker) |
| `.slugignore` | Excludes from buildpack slug |

---

## 4. Documentation Index

| Document | Location | Use |
|----------|----------|-----|
| Project Continuation Guide | `docs/PROJECT_CONTINUATION_GUIDE.md` | Main project overview |
| Heroku Deployment | `docs/HEROKU_DEPLOYMENT.md` | Full Heroku guide |
| Heroku 404 Fix | `docs/HEROKU_404_FIX.md` | Fix 404 on / |
| Heroku Backup | `docs/HEROKU_BACKUP_SETUP.md` | Postgres backup |
| Deployment Summary | `deployment-summary.txt` | High-level deploy summary |
| Moderation Flow | `docs/MODERATION_SURVEY_FLOW.md` | Moderation workflow |
| Scenario System | `docs/SCENARIO_SYSTEM.md` | Scenario generation |

---

## 5. Environment / Config Reference

### Heroku Config Vars (Recommended)

```
CORS_ALLOW_ORIGIN=https://yourapp.herokuapp.com;http://localhost:8080
VECTOR_DB=pgvector
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

Head revision after recent fixes: `u77v88w99x00` (and 38d63c18f30f for user table).

---

## 6. Debugging Quick Reference

| Symptom | Fix |
|---------|-----|
| 404 on /, /parents | Add nodejs buildpack before python; or use container stack |
| ModuleNotFoundError: azure | Ensure routers/openai.py has lazy import |
| Slug too large | Check .slugignore, requirements.txt |
| R14 Memory | WEB_CONCURRENCY=1, lazy imports |
| CORS warning | Set CORS_ALLOW_ORIGIN to explicit origins |
| Migration fails | Check Procfile release phase, migration 38d63c18f30f |

---

## 7. Routes and API Summary

**Frontend routes** (SvelteKit): /, /parent, /parents, /moderation, /initial-survey, /exit-survey, /kids/profile, etc.

**Backend API** (prefixes): /api/v1/*, /openai/*, /ollama/*, /ws (socket)

**Health**: GET /health

---

## 8. Continuation Checklist

When resuming work:

1. Read `docs/PROJECT_CONTINUATION_GUIDE.md`
2. For Heroku: Read `docs/HEROKU_DEPLOYMENT.md`
3. Run migrations if DB schema changed: `cd backend/open_webui && alembic upgrade head`
4. For Heroku buildpack: Verify `heroku buildpacks -a APP` shows nodejs before python
5. For optional features: Add packages to requirements.txt per comments
