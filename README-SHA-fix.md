# Open-webui SHA Exposure Fix

Repository: https://github.com/darshitp091/Open-webui-SHA-bug-fixed

Original project: https://github.com/open-webui/open-webui

Related issue: https://github.com/open-webui/open-webui/issues/24992

Summary
-------
This branch contains a targeted security fix that prevents unauthenticated HTTP clients from retrieving application version and health information which could expose build hashes or commit identifiers.

What was changed (code-end)
--------------------------------
- `backend/open_webui/main.py`
  - Gated the following endpoints with `Depends(get_verified_user)` so they require authentication:
    - `GET /api/version` and `GET /version`
    - `GET /health` and `GET /healthz`
    - `GET /health/db` and `GET /healthz/db`
    - `GET /ready`

- `backend/open_webui/test/apps/webui/routers/test_version_security.py`
  - Added regression tests asserting unauthenticated requests return `401` and authenticated requests succeed.

Why this fixes the bug
----------------------
Before this change the endpoints returned `VERSION` and `WEBUI_BUILD_HASH`/liveness info to any HTTP client. Adding the `get_verified_user` dependency enforces authentication at the FastAPI layer, blocking anonymous access to these routes.

Remaining exposure vectors (what the repo owner / operators must do)
-----------------------------------------------------------------
Although the HTTP endpoints are now gated, the following can still expose build/version info to third parties and must be reviewed by the project owner:

- Startup banner / logs: the server prints `WEBUI_BUILD_HASH` at startup (see `backend/open_webui/main.py` and `backend/open_webui/env.py`). Remove or mask this value in production logs.
- Frontend bundle: `src/lib/constants.ts` or Svelte stores may embed `WEBUI_VERSION` into the client bundle; ensure the frontend no longer includes sensitive build identifiers.
- CI and release artifacts: CI logs, Docker images, and release artifacts may contain commit SHAs — audit CI and build artifacts.
- Monitoring / probes: liveness/readiness probes that rely on unauthenticated endpoints must be updated to authenticate, use an internal-only endpoint, or be allowed via an environment flag.

How to test locally
-------------------
1. Create and activate the Python environment and install dependencies per upstream `pyproject.toml`.
2. Run the backend tests for the changed files:

```bash
python -m pytest backend/open_webui/test/apps/webui/routers/test_version_security.py -q
```

3. Start the backend and try the endpoints unauthenticated:

```bash
# expect 401
curl -i http://localhost:8000/api/version
curl -i http://localhost:8000/healthz
```

4. Authenticate (use the project's existing development test helpers or token) and retry; expect 200.

PR template / message
---------------------
Title: security: require auth for version & health endpoints

Body (suggested):

This PR gates the `/api/version`, `/version`, `/health`, `/healthz`, `/health/db`, `/healthz/db` and `/ready` endpoints with the existing authentication dependency `get_verified_user` to prevent unauthenticated disclosure of version and build information.

Fixes: https://github.com/open-webui/open-webui/issues/24992

Notes for maintainers:
- Update any external monitoring or Kubernetes probes to authenticate or call an internal-only health endpoint.
- Consider removing `WEBUI_BUILD_HASH` from the startup banner/logs and auditing the frontend bundle for embedded build identifiers.

Contact
-------
If you want, I can (A) prepare a pushable branch and instructions for you to push, or (B) push to this repo if you provide write access (recommended: add the remote and push locally yourself using the commands below).

Commands to push and open a PR (run locally in repository root)

```bash
# create branch and push
git checkout -b fix/security/gate-version-health
git add backend/open_webui/main.py backend/open_webui/test/apps/webui/routers/test_version_security.py README-SHA-fix.md
git commit -m "security: require auth for version & health endpoints; add regression test and README"
git remote add target-origin https://github.com/darshitp091/Open-webui-SHA-bug-fixed.git
git push -u target-origin fix/security/gate-version-health

# create PR with GitHub CLI
gh pr create --title "Require auth for version & health endpoints" --body "Fixes: https://github.com/open-webui/open-webui/issues/24992" --base main --head fix/security/gate-version-health
```

Credit
------
Patch prepared by: darshitp091
