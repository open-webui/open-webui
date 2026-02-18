# Heroku Deployment Guide

**Last Updated**: 2026-02-17  
**Project**: DSL KidsGPT Open WebUI

This document consolidates all Heroku deployment configuration, debugging history, and troubleshooting for this project.

---

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [GitHub Actions Automated Deployment](#github-actions-automated-deployment)
3. [Configuration Files](#configuration-files)
4. [Environment Variables](#environment-variables)
5. [Optional Packages (Lazy Imports)](#optional-packages-lazy-imports)
6. [Debugging History](#debugging-history)
7. [Troubleshooting](#troubleshooting)
8. [Known Heroku Apps](#known-heroku-apps)

---

## Deployment Options

The project supports two Heroku deployment strategies:

### Option A: Container Stack (Docker) – Recommended

Uses Heroku Container Registry. Frontend is built in the Dockerfile; no buildpack ordering concerns.

```bash
heroku stack:set container -a YOUR_APP_NAME
heroku addons:create heroku-postgresql:essential-0
git push heroku main
```

**Key files**: `Dockerfile`, `heroku.yml`

### Option B: Buildpack Stack

Uses Heroku buildpacks. **Node.js must run before Python** to build the frontend.

```bash
# Add Node.js first (builds frontend), then Python
heroku buildpacks:add --index 1 heroku/nodejs -a YOUR_APP_NAME
heroku buildpacks:add heroku/python -a YOUR_APP_NAME
heroku config:set NPM_CONFIG_PRODUCTION=false -a YOUR_APP_NAME  # Required: installs devDependencies for vite build
heroku addons:create heroku-postgresql:essential-0
git push heroku main
```

**Important**: `NPM_CONFIG_PRODUCTION=false` ensures devDependencies (vite, svelte, etc.) are installed for the frontend build.

**Key files**: `Procfile`, `app.json`, `requirements.txt` (root)

---

## GitHub Actions Automated Deployment

The repository includes a GitHub Actions workflow (`.github/workflows/heroku-deploy.yaml`) that automatically deploys to different Heroku apps based on the branch using container deployment:

- **Main branch** → `dsl-kidsgpt-pilot` (container deployment)
- **Dev branch** → `dsl-kidsgpt-pilot-alt` (container deployment)

### App Configuration

| Branch | App Name              | Stack     | Deployment Method         |
| ------ | --------------------- | --------- | ------------------------- |
| main   | dsl-kidsgpt-pilot     | container | Docker container registry |
| dev    | dsl-kidsgpt-pilot-alt | container | Docker container registry |

### Setup Instructions

**Required GitHub Secret:**

- Go to GitHub repository → Settings → Secrets and variables → Actions
- Add: `HEROKU_API_KEY` (get from: `heroku auth:token`)

**Configure environment variables** on Heroku apps:

```bash
# For main app (dsl-kidsgpt-pilot)
heroku config:set WEBUI_SECRET_KEY=$(openssl rand -hex 32) -a dsl-kidsgpt-pilot
heroku config:set OPENAI_API_KEY=your-openai-key -a dsl-kidsgpt-pilot
heroku config:set CORS_ALLOW_ORIGIN="https://dsl-kidsgpt-pilot.herokuapp.com" -a dsl-kidsgpt-pilot
heroku config:set VECTOR_DB=pgvector -a dsl-kidsgpt-pilot

# For dev app (dsl-kidsgpt-pilot-alt)
heroku config:set WEBUI_SECRET_KEY=$(openssl rand -hex 32) -a dsl-kidsgpt-pilot-alt
heroku config:set OPENAI_API_KEY=your-openai-key -a dsl-kidsgpt-pilot-alt
heroku config:set CORS_ALLOW_ORIGIN="https://dsl-kidsgpt-pilot-alt.herokuapp.com" -a dsl-kidsgpt-pilot-alt
heroku config:set VECTOR_DB=pgvector -a dsl-kidsgpt-pilot-alt
```

### Workflow Behavior

**Both branches use the same container deployment strategy:**

- **Triggers**: Pushes to `main` or `dev` branch, or manual workflow_dispatch
- **Process**:
  1. Checks out the repository
  2. Installs Heroku CLI
  3. Logs into Heroku Container Registry
  4. Builds Docker image with BUILD_HASH
  5. Pushes to Heroku Container Registry
  6. Releases the container to Heroku app

### Manual Deployment

You can trigger deployment manually from GitHub:

- Go to Actions → Deploy to Heroku → Run workflow
- Select the branch (main or dev) to deploy

---

## Configuration Files

| File               | Purpose                                                                           |
| ------------------ | --------------------------------------------------------------------------------- |
| `Procfile`         | Release phase (Alembic migrations) + web command. Used by buildpack deployment.   |
| `heroku.yml`       | Docker build/run config. Used when `heroku stack:set container`.                  |
| `app.json`         | Buildpack order for new apps (nodejs → python).                                   |
| `.slugignore`      | Excludes files from buildpack slug (keeps under 500MB).                           |
| `requirements.txt` | Root-level; used by buildpack. Backend uses `backend/requirements.txt` in Docker. |

### Release phase: heroku.yml vs Procfile

| Deployment method                                                                                 | Who builds the image     | Release phase source                                                                                                                       | When it runs                                                         |
| ------------------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| **Git push to Heroku** (`git push heroku main`) with `heroku.yml`                                 | Heroku (from heroku.yml) | **heroku.yml** `release:` section                                                                                                          | After Heroku build, before new release deploys. Procfile is ignored. |
| **Buildpack** (no Docker)                                                                         | Heroku (buildpacks)      | **Procfile** `release:` process type                                                                                                       | After build. No heroku.yml.                                          |
| **Container Registry** (e.g. GitHub Actions: build image → push → `heroku container:release web`) | You (CI)                 | **Neither** — release phase only runs if you build and push a **separate `release` image** and run `heroku container:release web release`. |

**This project’s current setup:** The app is deployed via **GitHub Actions** (`.github/workflows/heroku-container-deploy.yml`): the workflow builds the Docker image, pushes it, and runs `heroku container:release web` (no `release` image). So **the platform is not using heroku.yml or Procfile for the release phase**. Migrations run automatically when each **web dyno starts**: the container entrypoint is `backend/start.sh`, which runs `alembic upgrade head` before starting uvicorn (see “Migrations on web startup” below). You do not need to run them manually.

### Migrations on web startup

The container’s entrypoint is `backend/start.sh`. It runs `alembic upgrade head` in `/app/backend/open_webui` before starting the web server, so every new release’s web dynos run migrations as they boot. A separate “Run migrations” step in the workflow was removed because `heroku run` one-off dynos for container apps do not use the app image’s Python environment (they reported “No module named alembic”), so the reliable place for migrations is web startup.

### What is “Heroku build”? (GitHub integration vs our workflow)

- **Heroku build (GitHub integration)**  
  In the Heroku Dashboard you can connect the app to GitHub and enable “Deploy from GitHub” for a branch. Then **Heroku** runs the build on their servers on every push (using heroku.yml or buildpacks), and the release phase from heroku.yml runs automatically. You don’t run that manually; it’s triggered by the push. That’s a different path from our current one.

- **Our workflow (Container Registry via GitHub Actions)**  
  We don’t use Heroku to build. The **GitHub Actions** workflow builds the Docker image, pushes it to Container Registry, and runs `heroku container:release web`. Migrations run when the new web dynos start (see “Migrations on web startup” above). The workflow runs on push to the configured branches (and can be triggered manually via workflow_dispatch).

### Procfile

```
release: cd backend/open_webui && python -m alembic upgrade head
web: cd backend && uvicorn open_webui.main:app --host 0.0.0.0 --port $PORT
```

Used for buildpack deploys and as reference for paths; for container deploys from CI, the release phase is not run from Procfile (see table above).

### heroku.yml (Docker)

```yaml
build:
  docker:
    web: Dockerfile
release:
  command: cd /app/backend/open_webui && python -m alembic upgrade head || echo "Migration failed, continuing..."
```

Used when Heroku builds the image (e.g. `git push heroku main` with stack container). For Container Registry deploys from GitHub Actions, Heroku does not build from heroku.yml, so this release command is not used.

---

## Environment Variables

### Required for Heroku

- `DATABASE_URL` – Set automatically by Heroku Postgres addon
- `WEBUI_SECRET_KEY` – Session/auth secret
- `OPENAI_API_KEY` – For chat (if using OpenAI)

### Recommended for Production

| Variable            | Example                                               | Notes                                                          |
| ------------------- | ----------------------------------------------------- | -------------------------------------------------------------- |
| `CORS_ALLOW_ORIGIN` | `https://yourapp.herokuapp.com;http://localhost:8080` | **Do not use `*` in production.** Semicolon-separated origins. |
| `WEBUI_URL`         | `https://yourapp.herokuapp.com`                       | Required for OAuth/SSO.                                        |
| `VECTOR_DB`         | `pgvector`                                            | Use pgvector (chromadb removed for slug size).                 |

### Optional (Features Disabled for Heroku)

- `ENABLE_IMAGE_GENERATION=false`
- `AUDIO_STT_ENGINE=""`
- `AUDIO_TTS_ENGINE=""`
- `ENABLE_RAG_WEB_SEARCH=false`
- `ENABLE_RAG_LOCAL_WEB_FETCH=false`

---

## Optional Packages (Lazy Imports)

To reduce slug size and memory, several packages were removed from `requirements.txt` and made **lazy/conditional**. Install only if you need the feature:

| Package                         | Install when                                          | Command                                          |
| ------------------------------- | ----------------------------------------------------- | ------------------------------------------------ |
| `boto3`                         | STORAGE_PROVIDER=s3                                   | `pip install boto3`                              |
| `google-cloud-storage`          | STORAGE_PROVIDER=gcs                                  | `pip install google-cloud-storage`               |
| `azure-identity`                | STORAGE_PROVIDER=azure or Azure Document Intelligence | `pip install azure-identity`                     |
| `azure-storage-blob`            | STORAGE_PROVIDER=azure                                | `pip install azure-storage-blob`                 |
| `azure-ai-documentintelligence` | document_intelligence loader                          | `pip install azure-ai-documentintelligence`      |
| `ddgs`                          | DuckDuckGo search                                     | `pip install duckduckgo-search`                  |
| `firecrawl-py`                  | WEB_LOADER_ENGINE=firecrawl                           | `pip install firecrawl-py`                       |
| `tencentcloud-sdk-python`       | Sogou search                                          | `pip install tencentcloud-sdk-python`            |
| `opentelemetry-*`               | ENABLE_OTEL=true                                      | Multiple packages; see requirements.txt comments |

**Code changes**: Storage provider (`backend/open_webui/storage/provider.py`), loaders (`retrieval/loaders/main.py`), web search (`retrieval/web/*.py`), logger (`utils/logger.py`), and `routers/openai.py` use lazy imports with clear error messages when packages are missing.

---

## Debugging History

### 1. Slug Size Exceeded (567MB > 500MB)

- **Fix**: Expanded `.slugignore` (exclude data, notebooks, Docker files, CI, tests, videos). Removed heavy deps from `requirements.txt` (chromadb, playwright, transformers, etc.). Use `VECTOR_DB=pgvector`.
- **Config**: `backend/open_webui/config.py` sets `VECTOR_DB = os.environ.get("VECTOR_DB", "pgvector")`

### 2. ModuleNotFoundError at Startup

- **azure.identity**: `routers/openai.py` had top-level `from azure.identity import ...`. When azure packages were removed, app crashed. **Fix**: Moved import inside `get_microsoft_entra_id_access_token()` with `try/except ImportError`.
- **typer, mimeparse, etc.**: Added to `requirements.txt` as needed during deployment.

### 3. Database Migration Errors

- **UndefinedTable "config"**: Added `release` phase to Procfile: `cd backend/open_webui && python -m alembic upgrade head`
- **Multiple primary keys for table "user"**: Modified migration `38d63c18f30f` to conditionally create primary key (check existing constraints first).

### 4. Memory Quota Exceeded (R14)

- **Strategy**: Lazy imports for cloud SDKs, OpenTelemetry, Firecrawl, DDGS, Tencent. Removed optional packages from `requirements.txt`.
- **Heroku config**: `WEB_CONCURRENCY=1`, `MALLOC_ARENA_MAX=2` can help on 512MB dynos.

### 5. 404 on `/`, `/parents`, etc.

- **Cause**: Frontend `build/` directory missing at runtime. App serves API-only.
- **Fix (buildpack)**: Add `heroku/nodejs` buildpack **before** `heroku/python` so `npm run build` runs and creates `build/`.
- **Fix (Docker)**: Ensure `heroku stack:set container`; frontend is built in Dockerfile.
- **See**: `docs/HEROKU_404_FIX.md`

### 6. CORS Warning

- **Message**: `CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION`
- **Fix**: Set `CORS_ALLOW_ORIGIN` to explicit origins:  
  `heroku config:set CORS_ALLOW_ORIGIN="https://yourapp.herokuapp.com;http://localhost:8080"`

### 7. JavaScript Heap Out of Memory (OOM) During Build

- **Symptom**: Build fails with `FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory` during `npm run build`.
- **Cause**: The build runs `pyodide:fetch` (loads Pyodide in Node – memory-heavy) and `vite build` (large SvelteKit app). Combined, they exceed Node's default heap (~1.5–2GB).
- **Fix**: Increase Node heap via Heroku config:
  ```bash
  heroku config:set NODE_OPTIONS="--max-old-space-size=4096" -a YOUR_APP_NAME
  ```
- **Alternative**: If config var doesn't take effect during build, edit `package.json`:
  ```json
  "build": "NODE_OPTIONS=--max-old-space-size=4096 npm run pyodide:fetch && NODE_OPTIONS=--max-old-space-size=4096 vite build"
  ```
- **Note**: `WEB_CONCURRENCY` and `MALLOC_ARENA_MAX` apply to the Python runtime, not the Node build. Do not change them to fix build OOM.

### 8. No module named 'alembic' at Web Startup (Container)

- **Symptom**: Logs show `Database migrations failed! Container will not start` and `python3: No module named alembic` when the web dyno runs `backend/start.sh`.
- **Cause**: The Docker image was built with `pip install -r requirements.txt` failing (e.g. timeout, OOM, or dependency conflict). The Dockerfile had `|| ... continuing anyway`, so the build succeeded but the image was missing alembic and other packages.
- **Fix**: The Dockerfile was updated to (1) install `alembic` in the critical-packages block (so it is always present even if the full requirements step fails), (2) remove “continuing anyway” so a failed requirements install fails the build, and (3) verify `alembic` is importable after install. Rebuild the image via GitHub Actions and redeploy.

### 9. Error updating models: No module named 'sentence_transformers'

- **Symptom**: Log line `ERROR:open_webui.main:Error updating models: No module named 'sentence_transformers'` during startup.
- **Cause**: RAG reranker/embedding setup imports `sentence_transformers`; the exception is caught so the app continues, but the error is logged.
- **Fix**: Non-fatal. Ensure `sentence-transformers` is in `backend/requirements.txt`; the runtime dependency checker (`check_dependencies.py`) can install it if the mapping `sentence_transformers` → `sentence-transformers` is present.

---

## Troubleshooting

| Symptom                                                            | Likely cause                                                                                     | See                                                                                                                       |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| 404 on `/` or frontend routes                                      | Frontend not built (buildpack) or wrong stack                                                    | [HEROKU_404_FIX.md](HEROKU_404_FIX.md)                                                                                    |
| `ModuleNotFoundError: No module named 'azure'`                     | azure-identity removed; lazy import in openai router                                             | Ensure latest `routers/openai.py`                                                                                         |
| Slug too large                                                     | Heavy deps or large files in slug                                                                | `.slugignore`, `requirements.txt`                                                                                         |
| R14 Memory quota exceeded                                          | Too many workers or heavy imports                                                                | `WEB_CONCURRENCY=1`, lazy imports                                                                                         |
| Migration fails (UndefinedTable, InvalidTableDefinition)           | Release phase or migration script                                                                | Procfile release, migration `38d63c18f30f`                                                                                |
| CORS errors in browser                                             | `CORS_ALLOW_ORIGIN='*'` in production                                                            | Set explicit origins                                                                                                      |
| **Node OOM during build**                                          | `npm run build` exceeds heap limit                                                               | Set `NODE_OPTIONS=--max-old-space-size=4096`                                                                              |
| `npm ci` "Missing from lock file"                                  | package.json and package-lock.json out of sync                                                   | See [Lockfile Sync](#lockfile-sync) below                                                                                 |
| **No module named 'alembic'** / migrations failed at startup       | Full `pip install -r requirements.txt` failed during Docker build; image shipped without alembic | Dockerfile now installs alembic in the critical-packages step and verifies it after install. Rebuild and redeploy.        |
| **Error updating models: No module named 'sentence_transformers'** | RAG reranker/embedding code imports sentence_transformers; optional at startup                   | Non-fatal (app continues). Runtime checker can install it; ensure `sentence-transformers` is in backend/requirements.txt. |

### Lockfile Sync

When Heroku fails with `npm ci can only install packages when your package.json and package-lock.json are in sync` and lists "Missing from lock file" packages:

1. **Regenerate the lockfile**: Delete `package-lock.json` and `node_modules`, then run `npm install`.
2. **Pin npm version**: Use `engines.npm: "10.x"` in package.json to match Node 20.x (Heroku uses npm 10.x with Node 20).
3. **Commit and redeploy**: `git add package-lock.json package.json && git commit -m "Sync lockfile" && git push heroku main`.

If it still fails (platform-specific optional deps), regenerate the lockfile in a Linux environment (e.g. Docker: `docker run --rm -v $(pwd):/app -w /app node:20 npm install`).

### Verify Stack and Buildpacks

```bash
heroku stack -a YOUR_APP_NAME          # container vs heroku-22/24
heroku buildpacks -a YOUR_APP_NAME     # nodejs must be before python
```

### View Logs

```bash
heroku logs --tail -a YOUR_APP_NAME
```

---

## Known Heroku Apps

| App                             | Stack                 | Branch                      | Deployment Method                   | Notes                              |
| ------------------------------- | --------------------- | --------------------------- | ----------------------------------- | ---------------------------------- |
| `dsl-kidsgpt-pilot`             | container             | main                        | Container registry (GitHub Actions) | Production app - Docker container  |
| `dsl-kidsgpt-pilot-alt`         | container             | dev                         | Container registry (GitHub Actions) | Development app - Docker container |
| `contextquiz-openwebui-kidsgpt` | container (Docker)    | -                           | Manual                              | Legacy production app              |
| App                             | Stack                 | Notes                       |
| ------------------------------- | --------------------- | --------------------------- |
| `contextquiz-openwebui-kidsgpt` | container (Docker)    | Primary production app      |
| `dsl-kidsgpt-pilot`             | heroku-24 (buildpack) | Node.js + Python buildpacks |

---

## Related Documentation

- [HEROKU_404_FIX.md](HEROKU_404_FIX.md) – Fix 404 on root and frontend routes
- [HEROKU_BACKUP_SETUP.md](HEROKU_BACKUP_SETUP.md) – Postgres backup configuration
- [deployment-summary.txt](../deployment-summary.txt) – High-level deployment summary
