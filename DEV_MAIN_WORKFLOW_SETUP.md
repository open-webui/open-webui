# Dev → Main Workflow Setup Guide

**Target**: `feature/* → dev → main` deployment strategy

---

## Overview

This setup implements a two-stage deployment workflow:

- **`dev` branch**: Staging/integration testing
- **`main` branch**: Production deployments

Both branches automatically deploy to Heroku when code is merged.

---

## Step 1: Create Dev Branch

```bash
# Ensure you're on main and it's up to date
git checkout main
git pull origin main

# Create dev branch from main
git checkout -b dev
git push -u origin dev
```

---

## Step 2: Update Heroku Deploy Workflow

**File**: `.github/workflows/heroku-container-deploy.yml`

**Current content** (lines 3-14):

```yaml
on:
  push:
    branches:
      - main # Production deployments
      # - dev       # Uncomment for staging deployments (requires separate Heroku app)
      - cursor/heroku-build-memory-e9e1 # Legacy: remove after merging to main
  workflow_dispatch:

env:
  # Use different app for dev vs main (if staging is set up)
  # For now, all deployments go to production app
  HEROKU_APP_NAME: dsl-kidsgpt-pilot-alt
```

**Replace with**:

```yaml
on:
  push:
    branches:
      - main # Production deployments
      - dev # Staging deployments
      - cursor/heroku-build-memory-e9e1 # Legacy: remove after merging to main
  workflow_dispatch:

env:
  # Use different Heroku app based on branch
  # Option A: Same app for both (dev deploys to production, overwrites it)
  # HEROKU_APP_NAME: dsl-kidsgpt-pilot-alt

  # Option B: Separate staging app (recommended)
  # Requires creating a second Heroku app: dsl-kidsgpt-pilot-staging
  HEROKU_APP_NAME: ${{ github.ref == 'refs/heads/main' && 'dsl-kidsgpt-pilot-alt' || 'dsl-kidsgpt-pilot-alt' }}
```

**Note**: For now, both `dev` and `main` deploy to the same app (`dsl-kidsgpt-pilot-alt`). If you want separate staging, create a second Heroku app and update the conditional above.

---

## Step 3: Update Other Workflows (Optional)

The following workflows already trigger on both `main` and `dev`:

- ✅ `format-build-frontend.yaml` - Already triggers on `main` and `dev`
- ✅ `format-backend.yaml` - Already triggers on `main` and `dev`

No changes needed for these.

---

## Step 4: Merge Current Feature Branch

Once the workflow is updated:

```bash
# Merge current feature branch to dev (for testing)
git checkout dev
git pull origin dev
git merge cursor/heroku-build-memory-e9e1
git push origin dev

# This will trigger deployment to Heroku (staging)
# Test the deployment, then merge to main:

git checkout main
git pull origin main
git merge dev
git push origin main

# This will trigger deployment to Heroku (production)
```

---

## Workflow Diagram

```
Developer creates feature branch
  ↓
feature/my-feature
  ↓
Create PR: feature/my-feature → dev
  ↓
Merge to dev
  ↓
[Auto-deploy to Heroku staging]
  ↓
Test on staging
  ↓
Create PR: dev → main
  ↓
Merge to main
  ↓
[Auto-deploy to Heroku production]
```

---

## Daily Workflow

### For New Features

1. **Create feature branch from dev**:

   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/my-feature
   ```

2. **Develop and commit**:

   ```bash
   # Make changes
   git add .
   git commit -m "Add feature X"
   git push -u origin feature/my-feature
   ```

3. **Create PR to dev**:
   - PR: `feature/my-feature` → `dev`
   - CI runs: Format checks, build tests
   - Review and merge

4. **Test on staging** (after merge to dev):
   - GitHub Actions auto-deploys to Heroku
   - Test the deployed app
   - Check logs: `heroku logs --tail -a dsl-kidsgpt-pilot-alt`

5. **Promote to production**:
   - Create PR: `dev` → `main`
   - Review and merge
   - GitHub Actions auto-deploys to Heroku (production)

### For Hotfixes

1. **Create hotfix from main**:

   ```bash
   git checkout main
   git checkout -b hotfix/critical-fix
   ```

2. **Fix and merge directly to main**:

   ```bash
   # Make fix
   git commit -m "Fix critical issue"
   git push -u origin hotfix/critical-fix
   # Create PR: hotfix/critical-fix → main
   # Merge immediately (bypasses dev)
   ```

3. **Backport to dev**:
   ```bash
   git checkout dev
   git merge main
   git push origin dev
   ```

---

## Monitoring Deployments

### Check GitHub Actions

**Dev deployments**:
https://github.com/jjdrisco/DSL-kidsgpt-open-webui/actions?workflow=Deploy+to+Heroku+Container+Registry&branch=dev

**Main deployments**:
https://github.com/jjdrisco/DSL-kidsgpt-open-webui/actions?workflow=Deploy+to+Heroku+Container+Registry&branch=main

### Check Heroku

```bash
# Check latest release
heroku releases -a dsl-kidsgpt-pilot-alt

# Check dyno state
heroku ps -a dsl-kidsgpt-pilot-alt

# Check health
curl https://dsl-kidsgpt-pilot-alt-c8da0fb33a58.herokuapp.com/health

# Check logs
heroku logs --tail -a dsl-kidsgpt-pilot-alt
```

---

## Optional: Separate Staging App

If you want `dev` to deploy to a separate staging app:

1. **Create staging app**:

   ```bash
   heroku create dsl-kidsgpt-pilot-staging
   heroku stack:set container -a dsl-kidsgpt-pilot-staging
   ```

2. **Update workflow**:

   ```yaml
   env:
     HEROKU_APP_NAME: ${{ github.ref == 'refs/heads/main' && 'dsl-kidsgpt-pilot-alt' || 'dsl-kidsgpt-pilot-staging' }}
   ```

3. **Set up staging app** (same as production):
   - Add PostgreSQL: `heroku addons:create heroku-postgresql:essential-0 -a dsl-kidsgpt-pilot-staging`
   - Set config vars: `heroku config:set KEY=value -a dsl-kidsgpt-pilot-staging`
   - Add `HEROKU_API_KEY` secret to GitHub (same as production)

---

## Current Status

- ✅ Formatting fixes committed and pushed
- ⏳ Workflow file needs manual update (requires token with `workflow` scope)
- ⏳ Dev branch needs to be created
- ⏳ Feature branch needs to be merged to dev, then dev to main

---

## Next Steps

1. **Update workflow file** via GitHub UI (see Step 2 above)
2. **Create dev branch** (see Step 1)
3. **Merge feature branch** → dev → main (see Step 4)
4. **Test the workflow** with a small change

---

See `docs/DEPLOYMENT_WORKFLOW.md` for complete workflow documentation.
