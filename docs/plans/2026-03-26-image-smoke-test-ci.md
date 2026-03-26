# Image Smoke Test CI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a GitHub Actions workflow that builds the Docker image and confirms the app boots by hitting `/api/version`.

**Architecture:** Single workflow file, single job, single platform (linux/amd64). Full image build (no USE_SLIM) with GHA layer caching. Container runs with SQLite fallback (no DATABASE_URL), hits the unauthenticated `/api/version` endpoint to confirm the backend is up. Cleans up container in an `always()` step.

**Tech Stack:** GitHub Actions, Docker Buildx, `docker/build-push-action@v6`, `jq`, `curl`

---

### Task 1: Create the workflow file

**Files:**
- Create: `.github/workflows/image-smoke-test.yml`

**Step 1: Create the file with the following exact content**

```yaml
name: Image Smoke Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image
        uses: docker/build-push-action@v6
        with:
          context: .
          load: true
          tags: open-webui:smoke-test
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            BUILD_HASH=${{ github.sha }}

      - name: Start container
        run: |
          docker run -d \
            --name owui-smoke \
            -p 8080:8080 \
            -e WEBUI_SECRET_KEY=ci-test-key \
            -e WEBUI_AUTH=false \
            open-webui:smoke-test

      - name: Wait for app to boot
        run: |
          timeout 120 bash -c \
            'until curl -sf http://localhost:8080/api/version; do
               echo "waiting..."; sleep 5
             done'

      - name: Assert /api/version responds with version field
        run: |
          curl -sf http://localhost:8080/api/version | jq -e '.version != null'

      - name: Cleanup
        if: always()
        run: docker rm -f owui-smoke || true
```

**Step 2: Commit**

```bash
git add .github/workflows/image-smoke-test.yml
git commit -m "ci: add image smoke test workflow"
```

**Step 3: Push to trigger the workflow**

```bash
git push origin main
```

**Step 4: Verify the workflow runs**

Go to `https://github.com/venomx-pentester/open-webui/actions` and confirm:
- The `Image Smoke Test` workflow appears and runs
- The `smoke-test` job passes all steps
- The "Assert /api/version" step outputs JSON with a `version` field

---

## Notes

**Why `load: true` instead of `push: true`:**
The image is only needed locally to run the smoke test. No registry credentials needed, no push.

**Why no `DATABASE_URL`:**
Open-webui falls back to SQLite when `DATABASE_URL` is not set. This is enough to boot the app and serve `/api/version`.

**Why `WEBUI_AUTH=false`:**
Disables the auth signup wall so the app initializes cleanly without needing a seeded admin user.

**Why `concurrency`:**
Cancels in-progress runs on the same branch when a new push arrives. Prevents queued PR builds from piling up during rapid iteration.

**Why full build (no USE_SLIM):**
The venomx-docker compose builds this image without `USE_SLIM`, so CI should match. `USE_SLIM=true` skips model downloads and could hide broken pip deps or download URLs.

**GHA layer cache:**
`type=gha` stores Docker layer cache in GitHub Actions cache. Cold build ~25–35 min, warm build ~10–15 min. Cache is scoped per branch by default.
