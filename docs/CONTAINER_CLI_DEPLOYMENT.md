# Container Registry CLI Deployment Guide

## Why Container Registry CLI Works Better

### The Problem with API/Git Push Method

When using `git push heroku` or API builds with Container Registry:

1. **Heroku fetches entire repo first** (2.8GB in our case)
2. **Then builds Docker image** on Heroku's servers
3. **"Unknown error" occurs** during the fetch phase - likely due to:
   - Repository size (2.8GB) causing timeouts
   - GitHub tarball generation issues for large repos
   - Network/transfer limits

### Why Container Registry CLI Works

The `heroku container:push` command:

1. **Builds Docker image locally** (or in CI) using your `.dockerignore`
2. **Only sends the built image** to Heroku (not the entire repo)
3. **Bypasses the code fetch step** entirely
4. **Uses `.dockerignore` effectively** - excludes large files from build context

## Key Advantages

1. **No 500MB slug size limit** - Container Registry has no size restrictions
2. **Faster deployments** - Only pushes the built image, not source code
3. **Better error handling** - Build errors visible locally before pushing
4. **Works with large repos** - Doesn't need to fetch entire Git history

## Prerequisites

1. **Docker installed** locally or in CI environment
2. **Heroku CLI** with container plugin
3. **App configured** with `build_stack: container`

## Deployment Steps

### 1. Login to Container Registry

```bash
heroku container:login
# Or set HEROKU_API_KEY environment variable
export HEROKU_API_KEY="your-api-key"
heroku container:login
```

### 2. Build and Push Image

```bash
# Build and push the web process
heroku container:push web -a dsl-kidsgpt-pilot-alt

# Release the new image
heroku container:release web -a dsl-kidsgpt-pilot-alt
```

### 3. Verify Deployment

```bash
# Check app status
heroku ps -a dsl-kidsgpt-pilot-alt

# View logs
heroku logs --tail -a dsl-kidsgpt-pilot-alt
```

## Configuration Files

### heroku.yml

```yaml
build:
  docker:
    web: Dockerfile

release:
  command: cd open_webui && python -m alembic upgrade head

run:
  web: uvicorn open_webui.main:app --host 0.0.0.0 --port $PORT
```

### Dockerfile

- Already configured with `NODE_OPTIONS="--max-old-space-size=4096"`
- Multi-stage build (Node.js frontend + Python backend)
- Uses original `backend/requirements.txt` (no trimming needed)

### .dockerignore

- Excludes `node_modules`, `.git`, `build/`, `.svelte-kit/`
- Excludes `static/pyodide/` (generated during build)
- Reduces build context size significantly

## Troubleshooting

### If Docker is not available locally:

- Use GitHub Actions or other CI/CD to build and push
- Or use a remote Docker host

### If build fails:

- Check Dockerfile syntax: `docker build -t test .`
- Verify `.dockerignore` is working
- Check build logs: `heroku logs --tail -a dsl-kidsgpt-pilot-alt`

### If release fails:

- Check `heroku.yml` release command path
- Verify database migrations work: `cd open_webui && python -m alembic upgrade head`

## Current Status

- ✅ `heroku.yml` configured correctly
- ✅ `Dockerfile` has NODE_OPTIONS set
- ✅ `.dockerignore` excludes large files
- ✅ Original `backend/requirements.txt` restored
- ✅ Code changes reverted to original
- ⚠️ Docker not installed in current environment (needs local Docker or CI)

## Next Steps

1. Install Docker locally, OR
2. Set up CI/CD (GitHub Actions) to build and push container
3. Run `heroku container:push web -a dsl-kidsgpt-pilot-alt`
4. Run `heroku container:release web -a dsl-kidsgpt-pilot-alt`
