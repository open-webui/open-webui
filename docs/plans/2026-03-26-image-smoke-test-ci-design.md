# Image Smoke Test CI — Design

**Date:** 2026-03-26
**Status:** Approved

## Problem

The venomx-docker compose builds `open-webui` directly from this repo's `main` branch:

```yaml
build:
  context: https://github.com/venomx-pentester/open-webui.git#main
```

There is no CI gate on the image itself — only on formatting and releases. A broken push to `main` silently breaks the compose deploy.

## Goal

Lightweight image-level CI that validates the Docker image builds and the app boots. No postgres, redis, or vLLM needed.

## Approach

Full build + GitHub Actions layer cache (Approach B).

- Builds the same image the compose builds (no `USE_SLIM` flag)
- GHA layer cache makes warm runs tolerable (~10–15 min)
- Catches broken model downloads or pip deps that slim builds would hide

## Design

**File:** `.github/workflows/image-smoke-test.yml`

**Triggers:** `push` and `pull_request` to `main`

**Single job:** `smoke-test` on `ubuntu-latest`

### Steps

1. Checkout repo
2. Set up Docker Buildx
3. Build image — `docker/build-push-action` with `load: true`, GHA layer cache, `BUILD_HASH=${{ github.sha }}`
4. Start container — no `DATABASE_URL` (SQLite fallback), `WEBUI_SECRET_KEY=ci-test-key`, `WEBUI_AUTH=false`
5. Wait loop — poll `GET /api/version` with retries for up to 120s
6. Assert — `jq -e '.version'` confirms the backend is up and responding
7. Cleanup — `docker rm -f owui-smoke` in an `always()` step

### Why `/api/version`

- Unauthenticated endpoint (no auth dependency)
- Returns `{"version": ..., "deployment_id": ...}` — confirms the Python backend is running, not just the container
- Simpler than the `/health` endpoint (no `jq` boolean check needed)

## Out of Scope

- Database connectivity (SQLite only in CI)
- Auth flows
- ML model inference
- Multi-platform builds (linux/amd64 only)
- Pushing to any registry
