# Workflow File Update Instructions

**Status**: Workflow file needs manual update (token lacks `workflow` scope)

---

## Quick Update via GitHub UI

### Step 1: Navigate to Workflow File

Go to: https://github.com/jjdrisco/DSL-kidsgpt-open-webui/blob/cursor/heroku-build-memory-e9e1/.github/workflows/heroku-container-deploy.yml

### Step 2: Click "Edit" (Pencil Icon)

### Step 3: Update the `on:` Section

**Find** (lines 3-9):

```yaml
on:
  push:
    branches:
      - main # Production deployments
      # - dev       # Uncomment for staging deployments (requires separate Heroku app)
      - cursor/heroku-build-memory-e9e1 # Legacy: remove after merging to main
  workflow_dispatch:
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
```

### Step 4: Commit Directly to Branch

- Click "Commit changes"
- Use commit message: `Update Heroku deploy workflow for dev→main strategy`
- Commit directly to `cursor/heroku-build-memory-e9e1` branch

---

## Alternative: Update via Git with Workflow Scope Token

If you have a GitHub token with `workflow` scope:

```bash
# Update remote with token that has workflow scope
git remote set-url origin https://YOUR_TOKEN_WITH_WORKFLOW_SCOPE@github.com/jjdrisco/DSL-kidsgpt-open-webui.git

# Commit and push
git add .github/workflows/heroku-container-deploy.yml
git commit -m "Update Heroku deploy workflow for dev→main strategy"
git push -u origin cursor/heroku-build-memory-e9e1
```

---

## Complete Workflow File (Reference)

Here's the complete updated file for reference:

```yaml
name: Deploy to Heroku Container Registry

on:
  push:
    branches:
      - main # Production deployments
      - dev # Staging deployments
      - cursor/heroku-build-memory-e9e1 # Legacy: remove after merging to main
  workflow_dispatch:

env:
  # Use same app for both dev and main (dev overwrites production)
  # For separate staging app, change to:
  # HEROKU_APP_NAME: ${{ github.ref == 'refs/heads/main' && 'dsl-kidsgpt-pilot-alt' || 'dsl-kidsgpt-pilot-staging' }}
  HEROKU_APP_NAME: dsl-kidsgpt-pilot-alt

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Login to Heroku Container Registry
        run: |
          echo "${{ secrets.HEROKU_API_KEY }}" | docker login --username=_ --password-stdin registry.heroku.com
        env:
          HEROKU_API_KEY: ${{ secrets.HEROKU_API_KEY }}

      - name: Build Docker image
        run: |
          docker build -t registry.heroku.com/$HEROKU_APP_NAME/web .

      - name: Push to Heroku Container Registry
        run: |
          docker push registry.heroku.com/$HEROKU_APP_NAME/web

      - name: Install Heroku CLI
        run: |
          curl https://cli-assets.heroku.com/install.sh | sh

      - name: Release container
        run: |
          echo "$HEROKU_API_KEY" | heroku auth:token
          heroku container:release web -a $HEROKU_APP_NAME
        env:
          HEROKU_API_KEY: ${{ secrets.HEROKU_API_KEY }}

      - name: Check deployment status
        run: |
          echo "Waiting for dyno to start (max 5 minutes)..."
          timeout 300 bash -c 'until heroku ps:wait -a $HEROKU_APP_NAME --type web 2>/dev/null; do sleep 10; done' || echo "Dyno may still be starting"
          heroku ps -a $HEROKU_APP_NAME
          echo "Checking app health..."
          sleep 10
          curl -f https://$HEROKU_APP_NAME.herokuapp.com/health || echo "Health check failed - check logs"
        env:
          HEROKU_API_KEY: ${{ secrets.HEROKU_API_KEY }}
```

---

## After Updating Workflow

1. **Create dev branch** (if not exists):

   ```bash
   git checkout main
   git checkout -b dev
   git push -u origin dev
   ```

2. **Merge feature branch to dev**:

   ```bash
   git checkout dev
   git merge cursor/heroku-build-memory-e9e1
   git push origin dev
   # This will trigger first dev deployment
   ```

3. **Merge dev to main**:
   ```bash
   git checkout main
   git merge dev
   git push origin main
   # This will trigger production deployment
   ```

---

**See**: `DEV_MAIN_WORKFLOW_SETUP.md` for complete setup guide
