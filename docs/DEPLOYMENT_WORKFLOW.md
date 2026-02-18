# Deployment Workflow Strategy

**Last Updated**: 2026-02-10  
**Project**: DSL KidsGPT Open WebUI

This document outlines the recommended branch strategy and deployment workflow for managing development and production deployments.

---

## Branch Strategy

### Recommended Branch Structure

```
main (production)
  ↑
dev (staging/integration)
  ↑
feature/* (development branches)
```

### Branch Purposes

1. **`main`** - Production-ready code
   - Only merged from `dev` after testing
   - Triggers production Heroku deployment
   - Should always be stable and deployable

2. **`dev`** - Staging/Integration branch
   - Where feature branches merge for integration testing
   - Can trigger staging Heroku deployment (optional)
   - Used for pre-production testing

3. **`feature/*`** - Development branches
   - Individual features, bug fixes, experiments
   - Examples: `feature/new-ui`, `bugfix/dependency-checker`, `cursor/heroku-build-memory-e9e1`
   - Merge to `dev` when ready for integration

---

## Deployment Workflow

### Current Setup

**Heroku App**: `dsl-kidsgpt-pilot-alt`  
**Deployment Method**: GitHub Actions → Heroku Container Registry  
**Workflow File**: `.github/workflows/heroku-container-deploy.yml`

### Recommended Workflow

#### Option A: Single Production App (Recommended)

**Trigger**: Push to `main` branch

**Workflow**:

1. Developer works on feature branch (`feature/xyz`)
2. Merge feature branch → `dev` (for integration testing)
3. Test on `dev` branch (optional staging deployment)
4. Merge `dev` → `main` (triggers production deployment)
5. GitHub Actions automatically builds and deploys to Heroku

**Benefits**:

- ✅ Clear separation: dev (testing) vs main (production)
- ✅ Automatic deployments on merge to main
- ✅ Can test on dev before promoting to production
- ✅ Simple, linear workflow

**Configuration**:

```yaml
# .github/workflows/heroku-container-deploy.yml
on:
  push:
    branches:
      - main # Production deployments
  workflow_dispatch: # Manual trigger if needed
```

#### Option B: Separate Staging + Production Apps

**Trigger**:

- Push to `dev` → deploys to staging app
- Push to `main` → deploys to production app

**Workflow**:

1. Developer works on feature branch
2. Merge → `dev` (auto-deploys to staging app)
3. Test on staging
4. Merge `dev` → `main` (auto-deploys to production app)

**Benefits**:

- ✅ Can test deployments before production
- ✅ Staging environment matches production
- ✅ Catch issues before they hit production

**Configuration**:

```yaml
# .github/workflows/heroku-container-deploy.yml
on:
  push:
    branches:
      - main # Production
      - dev # Staging
  workflow_dispatch:

env:
  HEROKU_APP_NAME: ${{ github.ref == 'refs/heads/main' && 'dsl-kidsgpt-pilot-alt' || 'dsl-kidsgpt-pilot-staging' }}
```

---

## Migration Plan: Current → Recommended

### Step 1: Update Heroku Deploy Workflow

**Current**: Only triggers on `cursor/heroku-build-memory-e9e1`  
**Target**: Trigger on `main` (and optionally `dev`)

**Action**: Update `.github/workflows/heroku-container-deploy.yml`:

```yaml
on:
  push:
    branches:
      - main # Production deployments
      # - dev       # Uncomment for staging deployments
  workflow_dispatch: # Manual trigger
```

### Step 2: Merge Current Work to Main

**Current state**: All fixes are on `cursor/heroku-build-memory-e9e1`  
**Action**: Merge this branch → `main`

**Commands**:

```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Merge the feature branch
git merge cursor/heroku-build-memory-e9e1

# Push to trigger deployment
git push origin main
```

### Step 3: Set Up Dev Branch (Optional)

**Action**: Create `dev` branch from `main` for future development

**Commands**:

```bash
git checkout main
git checkout -b dev
git push -u origin dev
```

### Step 4: Update Workflow Documentation

**Action**: Update workflow triggers in documentation to reflect new branch strategy

---

## Daily Development Workflow

### For New Features

1. **Create feature branch**:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-feature
   ```

2. **Develop and commit**:

   ```bash
   # Make changes
   git add .
   git commit -m "Add feature X"
   git push -u origin feature/my-feature
   ```

3. **Create Pull Request**:
   - PR: `feature/my-feature` → `dev` (or `main` if skipping dev)
   - CI runs: Format checks, build tests
   - Review and merge

4. **Deploy**:
   - Merge to `main` triggers automatic Heroku deployment
   - Monitor GitHub Actions workflow
   - Check Heroku logs: `heroku logs --tail -a dsl-kidsgpt-pilot-alt`

### For Hotfixes

1. **Create hotfix branch from main**:

   ```bash
   git checkout main
   git checkout -b hotfix/critical-fix
   ```

2. **Fix and test**:

   ```bash
   # Make fix
   git commit -m "Fix critical issue"
   git push -u origin hotfix/critical-fix
   ```

3. **Merge directly to main**:
   - Create PR: `hotfix/critical-fix` → `main`
   - Merge immediately (bypasses dev)
   - Auto-deploys to production

4. **Backport to dev** (if applicable):
   ```bash
   git checkout dev
   git merge main
   git push origin dev
   ```

---

## CI/CD Pipeline

### Workflows That Run

1. **Format & Build Frontend** (`.github/workflows/format-build-frontend.yaml`)
   - **Triggers**: Push to `main`, `dev`, PRs
   - **Actions**: Format code, run i18n parse, build frontend
   - **Must pass**: `git diff --exit-code` (no uncommitted formatting)

2. **Format Backend** (`.github/workflows/format-backend.yaml`)
   - **Triggers**: Push to `main`, `dev`, PRs (when backend files change)
   - **Actions**: Format Python code with `black`
   - **Must pass**: `git diff --exit-code` (no uncommitted formatting)

3. **Deploy to Heroku** (`.github/workflows/heroku-container-deploy.yml`)
   - **Triggers**: Push to `main` (and optionally `dev`)
   - **Actions**: Build Docker image, push to Container Registry, release on Heroku
   - **Duration**: ~10-15 minutes

### Workflow Dependencies

```
Push to main/dev
  ↓
Format & Build Frontend (must pass)
  ↓
Format Backend (must pass)
  ↓
Deploy to Heroku (runs in parallel, doesn't block)
```

**Note**: Heroku deployment runs independently and doesn't block other workflows. However, formatting checks should pass before merging PRs.

---

## Best Practices

### 1. Always Run Formatters Before Committing

**Frontend**:

```bash
npm run format
npm run i18n:parse
git add -A
git commit -m "Apply frontend formatting"
```

**Backend**:

```bash
python3 -m black backend/ --exclude ".venv/|/venv/"
git add backend
git commit -m "Apply backend formatting"
```

### 2. Test Locally Before Pushing

**Check formatting**:

```bash
npm run format
npm run i18n:parse
python3 -m black backend/ --exclude ".venv/|/venv/"
git diff --exit-code  # Should be clean
```

**Test dependency checker** (if modified):

```bash
cd backend
python3 check_dependencies.py
```

### 3. Monitor Deployments

**After merging to main**:

1. Check GitHub Actions: https://github.com/jjdrisco/DSL-kidsgpt-open-webui/actions
2. Wait for "Deploy to Heroku Container Registry" workflow to complete (~10-15 min)
3. Check Heroku release: `heroku releases -a dsl-kidsgpt-pilot-alt`
4. Check dyno state: `heroku ps -a dsl-kidsgpt-pilot-alt`
5. Check health: `curl https://dsl-kidsgpt-pilot-alt-c8da0fb33a58.herokuapp.com/health`
6. Check logs: `heroku logs --tail -a dsl-kidsgpt-pilot-alt`

### 4. Use Descriptive Commit Messages

**Good**:

```
Fix dependency checker for langchain_text_splitters
Increase dependency checker attempts for deep import chains
Add comprehensive Heroku troubleshooting guide
```

**Bad**:

```
fix
update
changes
```

### 5. Keep Feature Branches Focused

- One feature/fix per branch
- Keep branches short-lived (merge within days/weeks)
- Delete branches after merging

---

## Rollback Procedure

### If Deployment Fails

1. **Check logs**:

   ```bash
   heroku logs --tail -a dsl-kidsgpt-pilot-alt
   ```

2. **Rollback to previous release**:

   ```bash
   heroku releases -a dsl-kidsgpt-pilot-alt  # Find previous version
   heroku rollback v42 -a dsl-kidsgpt-pilot-alt  # Rollback to v42
   ```

3. **Fix issue on feature branch**:

   ```bash
   git checkout -b hotfix/deployment-issue
   # Make fixes
   git commit -m "Fix deployment issue"
   git push -u origin hotfix/deployment-issue
   ```

4. **Merge and redeploy**:
   - Create PR: `hotfix/deployment-issue` → `main`
   - Merge when fixed
   - New deployment triggers automatically

---

## Current vs Recommended State

### Current State

- ✅ Heroku deployment working via GitHub Actions
- ✅ Runtime dependency checker implemented
- ✅ All fixes on `cursor/heroku-build-memory-e9e1` branch
- ⚠️ Workflow only triggers on feature branch (not main)
- ⚠️ No clear dev → main promotion path

### Recommended State

- ✅ Heroku deployment triggers on `main` branch
- ✅ Optional: Staging deployment on `dev` branch
- ✅ Feature branches → `dev` → `main` workflow
- ✅ Clear separation: development vs production
- ✅ Automatic deployments on merge to main

---

## Next Steps

1. **Update workflow file** to trigger on `main` (see migration plan above)
2. **Merge current branch** (`cursor/heroku-build-memory-e9e1`) → `main`
3. **Create `dev` branch** (optional, for staging)
4. **Update team documentation** with new workflow
5. **Test deployment** by merging a small change to main

---

## Related Documentation

- [Heroku Troubleshooting Guide](./HEROKU_TROUBLESHOOTING_GUIDE.md) - Detailed troubleshooting process
- [Heroku Deployment Guide](./HEROKU_DEPLOYMENT.md) - Configuration and setup
- [Project Continuation Guide](./PROJECT_CONTINUATION_GUIDE.md) - Overall project overview

---

**Last Updated**: 2026-02-10  
**Status**: 📋 Recommended workflow (not yet implemented)
