# Heroku Deployment Troubleshooting Guide

**Last Updated**: 2026-02-10  
**Project**: DSL KidsGPT Open WebUI  
**App**: `dsl-kidsgpt-pilot-alt`  
**Branch**: `cursor/heroku-build-memory-e9e1`

This document details the complete troubleshooting process for deploying this application to Heroku, including why we switched to GitHub Actions + Container Registry, the runtime dependency checker solution, and all commands used.

---

## Table of Contents

1. [Problem Overview](#problem-overview)
2. [Deployment Strategy Evolution](#deployment-strategy-evolution)
3. [Why GitHub Actions + Container Registry](#why-github-actions--container-registry)
4. [Runtime Dependency Checker Solution](#runtime-dependency-checker-solution)
5. [Troubleshooting Process](#troubleshooting-process)
6. [Commands Reference](#commands-reference)
7. [What Worked and What Didn't](#what-worked-and-what-didnt)
8. [Lessons Learned](#lessons-learned)

---

## Problem Overview

### Initial Challenges

1. **Node.js Memory Exhaustion**: Frontend build (`npm run build`) failed with:

   ```
   FATAL ERROR: Ineffective mark-compacts near heap limit
   Allocation failed - JavaScript heap out of memory
   ```

2. **Slug Size Limit**: Buildpack deployments exceeded Heroku's 500MB slug size limit:

   ```
   Compiled slug size: 1.2G is too large (max is 500M)
   ```

3. **Runtime ModuleNotFoundError**: After successful builds, dynos crashed on startup with missing Python modules:
   - `ModuleNotFoundError: No module named 'typer'`
   - `ModuleNotFoundError: No module named 'sqlalchemy'`
   - `ModuleNotFoundError: No module named 'bs4'`
   - `ModuleNotFoundError: No module named 'jwt'`
   - `ModuleNotFoundError: No module named 'langchain_text_splitters'`
   - `ModuleNotFoundError: No module named 'ftfy'`
   - And many more...

4. **Container Registry "Unknown Error"**: Direct `git push heroku` with Container Registry failed immediately:
   ```
   remote: === Fetching app code.
   remote: =!= Unknown error
   remote: ! Build failed to complete. Please try pushing again.
   ```

---

## Deployment Strategy Evolution

### Phase 1: Buildpack Deployment (Failed)

**Attempted**: Traditional Heroku buildpack deployment with Node.js + Python.

**Why it failed**:

- Slug size exceeded 500MB limit even after aggressive `.slugignore` exclusions
- Required complex buildpack ordering (Node.js before Python)
- Frontend build memory issues required `NODE_OPTIONS` config vars

**Commands tried**:

```bash
heroku buildpacks:add --index 1 heroku/nodejs -a dsl-kidsgpt-pilot-alt
heroku buildpacks:add heroku/python -a dsl-kidsgpt-pilot-alt
heroku config:set NODE_OPTIONS="--max-old-space-size=4096" -a dsl-kidsgpt-pilot-alt
git push heroku main
```

**Result**: ❌ Slug size too large (1.2GB > 500MB limit)

---

### Phase 2: Container Registry via Git Push (Failed)

**Attempted**: Switch to Container Registry stack and deploy via `git push heroku`.

**Why it failed**:

- Heroku's Container Registry fetch step failed with "Unknown error"
- Likely due to large repository size (2.8GB) or platform limitations
- No detailed error logs available

**Commands tried**:

```bash
heroku stack:set container -a dsl-kidsgpt-pilot-alt
git push heroku cursor/heroku-build-memory-e9e1:main
```

**Result**: ❌ "Unknown error" during code fetch (multiple build IDs failed)

---

### Phase 3: Container Registry via CLI (Partial Success)

**Attempted**: Build Docker image locally and push via Heroku Container Registry CLI.

**Why it partially worked**:

- ✅ Bypassed the problematic code fetch step
- ✅ Successfully built and pushed Docker image
- ✅ Container released successfully
- ❌ Dyno crashed on startup due to missing Python dependencies

**Commands used**:

```bash
heroku container:login
heroku container:push web -a dsl-kidsgpt-pilot-alt
heroku container:release web -a dsl-kidsgpt-pilot-alt
```

**Result**: ⚠️ Build succeeded, but runtime dependency issues persisted

---

### Phase 4: GitHub Actions + Container Registry (Current Solution)

**Why this works**:

- ✅ Builds Docker image in CI (no local Docker required)
- ✅ Only pushes built image (bypasses repo fetch issues)
- ✅ Automated on every push
- ✅ Better error visibility in GitHub Actions logs
- ✅ Can be triggered manually via `workflow_dispatch`

**Current workflow**: `.github/workflows/heroku-container-deploy.yml`

---

## Why GitHub Actions + Container Registry

### Advantages

1. **No Local Docker Required**: Build happens in GitHub's CI environment
2. **Bypasses Fetch Issues**: Only pushes the built image, not the entire repo
3. **Automated**: Runs on every push to the branch
4. **Better Logging**: Full Docker build logs visible in GitHub Actions
5. **Manual Trigger**: Can be triggered via GitHub UI if needed
6. **No Size Limits**: Container Registry has no 500MB slug size restriction

### Workflow Configuration

**File**: `.github/workflows/heroku-container-deploy.yml`

**Triggers**:

- Push to `cursor/heroku-build-memory-e9e1` branch
- Manual `workflow_dispatch`

**Steps**:

1. Checkout code
2. Login to Heroku Container Registry (using `HEROKU_API_KEY` secret)
3. Build Docker image
4. Push to Container Registry
5. Release container on Heroku
6. Check deployment status

**Required GitHub Secret**:

- `HEROKU_API_KEY`: Heroku API token with appropriate permissions

---

## Runtime Dependency Checker Solution

### The Core Problem

Even though `backend/requirements.txt` contains all necessary packages, the Docker build process was not installing them reliably. This led to runtime crashes with `ModuleNotFoundError` for packages that were:

- ✅ Listed in `requirements.txt`
- ✅ Should have been installed during build
- ❌ Missing at runtime

### Root Causes Identified

1. **Build-time installation failures**: `pip install -r requirements.txt` was configured to not fail the build (to allow optional packages)
2. **Deep import chains**: Some modules are only imported deep in the dependency tree, so missing packages weren't caught until runtime
3. **Module name mismatches**: Python import names don't always match pip package names (e.g., `bs4` → `beautifulsoup4`, `jwt` → `PyJWT`)

### Solution: Runtime Dependency Checker

**File**: `backend/check_dependencies.py`

**How it works**:

1. Attempts to import `open_webui.main` (which triggers all application imports)
2. Catches `ModuleNotFoundError` exceptions
3. Maps missing module names to pip package names
4. Installs missing packages from `requirements.txt`
5. Retries import (up to 60 attempts for deep chains)
6. Reports success when all imports succeed

**Key Features**:

- **Module-to-pip mapping**: Handles common mismatches (`bs4` → `beautifulsoup4`, etc.)
- **Exact match preference**: Prefers exact normalized matches from `requirements.txt` before fuzzy matching
- **Deep chain support**: Up to 60 retry attempts to handle cascading dependencies
- **Error reporting**: Shows pip stdout/stderr on installation failures

**Integration**: Called from `backend/start.sh` before starting uvicorn:

```bash
# Run comprehensive dependency checker (automatically installs missing packages)
echo "Verifying critical packages..."
if $PYTHON_CMD /app/backend/check_dependencies.py 2>&1; then
    echo "✓ All critical packages verified"
else
    echo "WARNING: Some dependencies may be missing, but continuing..."
fi
```

---

## Troubleshooting Process

### Step-by-Step Debugging

#### 1. Identify the Missing Module

**Command**:

```bash
heroku logs --tail -a dsl-kidsgpt-pilot-alt
```

**Look for**:

```
ModuleNotFoundError: No module named 'MODULE_NAME'
```

#### 2. Check if Package is in requirements.txt

**Command**:

```bash
grep -i "MODULE_NAME\|PACKAGE_NAME" backend/requirements.txt
```

**Example**: For `bs4` error, check for `beautifulsoup4`:

```bash
grep beautifulsoup4 backend/requirements.txt
```

#### 3. Verify Module-to-Pip Mapping

**Check**: `backend/check_dependencies.py` → `MODULE_TO_PIP` dictionary

**If missing**, add mapping:

```python
MODULE_TO_PIP = {
    ...
    "missing_module": "pip-package-name",
}
```

#### 4. Test Locally (Optional)

**Command**:

```bash
python3 -c "import missing_module"
```

If this fails locally, the package needs to be added to `requirements.txt`.

#### 5. Update Dependency Checker

**If module name ≠ pip package name**:

- Add to `MODULE_TO_PIP` mapping in `check_dependencies.py`

**If checker runs out of attempts**:

- Increase `max_attempts` (currently 60)

**If exact match fails**:

- Verify normalization logic (`_norm()` function)
- Check that `requirements.txt` has the correct package name

#### 6. Commit and Deploy

**Commands**:

```bash
git add backend/check_dependencies.py
git commit -m "Fix dependency checker for MODULE_NAME"
git push -u origin cursor/heroku-build-memory-e9e1
```

**Monitor**:

- GitHub Actions workflow: https://github.com/jjdrisco/DSL-kidsgpt-open-webui/actions
- Heroku logs: `heroku logs --tail -a dsl-kidsgpt-pilot-alt`

#### 7. Verify Success

**Check dyno state**:

```bash
heroku ps -a dsl-kidsgpt-pilot-alt
```

**Check health endpoint**:

```bash
curl https://dsl-kidsgpt-pilot-alt-c8da0fb33a58.herokuapp.com/health
```

**Check logs for dependency checker**:

```bash
heroku logs --tail -a dsl-kidsgpt-pilot-alt | grep -E "(Dependency check|Missing module|All dependencies satisfied)"
```

---

## Commands Reference

### GitHub Actions Monitoring

**Check latest workflow run**:

```bash
curl -s -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/jjdrisco/DSL-kidsgpt-open-webui/actions/workflows/heroku-container-deploy.yml/runs?per_page=1" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['status'], r.get('conclusion'), r['head_sha'][:7])"
```

**Check specific run**:

```bash
curl -s -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/jjdrisco/DSL-kidsgpt-open-webui/actions/runs/RUN_ID" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['status'], r.get('conclusion'))"
```

### Heroku Monitoring

**Check latest release**:

```bash
curl -s "https://api.heroku.com/apps/dsl-kidsgpt-pilot-alt/releases" \
  -H "Accept: application/vnd.heroku+json; version=3" \
  -H "Authorization: Bearer YOUR_HEROKU_API_KEY" \
  | python3 -c "import sys,json; rel=json.load(sys.stdin); latest=sorted(rel, key=lambda x:int(x.get('version',0)), reverse=True)[0]; print('v'+str(latest.get('version')), latest.get('status'))"
```

**Check dyno state**:

```bash
curl -s "https://api.heroku.com/apps/dsl-kidsgpt-pilot-alt/dynos/web.1" \
  -H "Accept: application/vnd.heroku+json; version=3" \
  -H "Authorization: Bearer YOUR_HEROKU_API_KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state'), d.get('updated_at'))"
```

**Fetch logs**:

```bash
heroku logs --tail -a dsl-kidsgpt-pilot-alt
```

**Or via API**:

```bash
URL=$(curl -s -X POST "https://api.heroku.com/apps/dsl-kidsgpt-pilot-alt/log-sessions" \
  -H "Accept: application/vnd.heroku+json; version=3" \
  -H "Authorization: Bearer YOUR_HEROKU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lines": 200, "tail": false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('logplex_url',''))")
curl -sL "$URL" | tail -200
```

**Check health**:

```bash
curl -s "https://dsl-kidsgpt-pilot-alt-c8da0fb33a58.herokuapp.com/health" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Health:', d.get('status'))"
```

### Local Testing

**Format backend code**:

```bash
python3 -m black backend/ --exclude ".venv/|/venv/"
```

**Format frontend code**:

```bash
npm run format
npm run i18n:parse
```

**Test dependency checker locally**:

```bash
cd backend
python3 check_dependencies.py
```

**Build Docker image locally** (optional):

```bash
docker build -t test-image .
docker run --rm test-image python3 /app/backend/check_dependencies.py
```

---

## What Worked and What Didn't

### ✅ What Worked

1. **GitHub Actions + Container Registry**
   - Automated builds on every push
   - No local Docker required
   - Bypassed repo fetch issues

2. **Runtime Dependency Checker**
   - Automatically installs missing packages at startup
   - Handles deep import chains (60 attempts)
   - Module-to-pip name mapping

3. **Exact Match Preference**
   - Fixed `langchain_text_splitters` → `langchain-text-splitters` issue
   - Prevents fuzzy matching from grabbing wrong packages

4. **Increased Max Attempts**
   - From 20 → 60 attempts
   - Allows checker to resolve entire dependency chain

5. **Better Error Reporting**
   - Shows pip stdout/stderr on failures
   - Easier to debug installation issues

### ❌ What Didn't Work

1. **Buildpack Deployment**
   - Slug size exceeded 500MB limit
   - Even with aggressive `.slugignore` exclusions

2. **Direct Git Push to Container Registry**
   - "Unknown error" during code fetch
   - No detailed error logs
   - Multiple build IDs failed consistently

3. **Build-time Strict Dependency Installation**
   - Made Docker builds fail when optional packages had issues
   - Required allowing build to continue with missing packages

4. **Fuzzy Matching First**
   - Caused `langchain_text_splitters` to match `langchain==1.2.0` instead of `langchain-text-splitters==1.1.0`
   - Fixed by preferring exact matches

5. **Low Max Attempts (20)**
   - Insufficient for deep import chains
   - Checker stopped before installing `ftfy` (attempt 21)

---

## Lessons Learned

### 1. Container Registry Requires Different Approach

**Lesson**: Heroku Container Registry has different failure modes than buildpacks. The "Unknown error" during code fetch suggests platform limitations or timeouts for large repos.

**Solution**: Build Docker image externally (GitHub Actions) and only push the built image.

### 2. Runtime Dependency Resolution is Necessary

**Lesson**: Even with `requirements.txt`, build-time installation can fail silently or miss dependencies due to:

- Optional package handling
- Build optimization (not installing everything)
- Deep import chains not caught until runtime

**Solution**: Runtime dependency checker that validates imports and installs missing packages.

### 3. Module Name ≠ Pip Package Name

**Lesson**: Python import names don't always match pip package names:

- `bs4` → `beautifulsoup4`
- `jwt` → `PyJWT`
- `langchain_text_splitters` → `langchain-text-splitters`

**Solution**: Maintain a `MODULE_TO_PIP` mapping dictionary.

### 4. Exact Matching Before Fuzzy Matching

**Lesson**: Fuzzy "contains" matching can grab wrong packages:

- `langchain_text_splitters` matched `langchain==1.2.0` (contains "langchain")
- Should have matched `langchain-text-splitters==1.1.0` (exact normalized match)

**Solution**: Two-pass matching: exact normalized matches first, then fuzzy fallback.

### 5. Deep Import Chains Require Many Attempts

**Lesson**: Some applications have deep, cascading import dependencies:

- Attempt 1-14: Core dependencies
- Attempt 15-19: Secondary dependencies
- Attempt 20: `langchain_text_splitters`
- Attempt 21: `ftfy`
- Attempt 22-29: More dependencies
- Attempt 29: All satisfied

**Solution**: Increase `max_attempts` to 60 (or higher if needed).

### 6. Formatting Checks Must Be Committed

**Lesson**: CI workflows run formatters (`black`, `prettier`, `i18n:parse`) and expect clean git diffs. Uncommitted formatting changes cause CI failures.

**Solution**: Always run formatters locally and commit changes before pushing:

```bash
npm run format
npm run i18n:parse
python3 -m black backend/ --exclude ".venv/|/venv/"
git add -A
git commit -m "Apply formatting"
git push
```

---

## Current Deployment Status

**App**: `dsl-kidsgpt-pilot-alt`  
**Stack**: `container`  
**Deployment Method**: GitHub Actions → Heroku Container Registry  
**Latest Release**: `v43` (succeeded)  
**Dyno State**: `up`  
**Health**: `status: True`

**Dependency Checker**: Successfully resolving runtime dependencies (29 attempts to satisfy all imports)

---

## Future Improvements

1. **Pre-install Critical Dependencies**: Consider installing more packages at Docker build time to reduce runtime installation
2. **Cache Installed Packages**: Persist installed packages between dyno restarts (if using ephemeral filesystem, this won't help)
3. **Health Check Endpoint**: Verify dependency checker ran successfully
4. **Monitoring**: Alert if dependency checker exceeds certain attempt thresholds
5. **Documentation**: Keep `MODULE_TO_PIP` mapping updated as new mismatches are discovered

---

## Related Documentation

- [Heroku Deployment Guide](./HEROKU_DEPLOYMENT.md) - General deployment configuration
- [Heroku 404 Fix](./HEROKU_404_FIX.md) - Frontend routing issues
- [Project Continuation Guide](./PROJECT_CONTINUATION_GUIDE.md) - Overall project overview

---

**Last Updated**: 2026-02-10  
**Author**: Cloud Agent (Auto)  
**Status**: ✅ Deployment successful, app running
