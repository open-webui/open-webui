# Fixing 404 on Heroku (Root and Frontend Routes)

## Symptom

- `GET /` returns 404
- `GET /parents`, `/home`, etc. return 404
- API routes like `/api/v1/...` may work

## Cause

The frontend build (`build/` from `npm run build`) is missing at runtime. Without it, the app serves API-only and returns 404 for all non-API routes.

## Fix by Deployment Type

### Option A: Container Stack (Docker) – Recommended

If your app uses **Docker** (container stack), the frontend is built in the Dockerfile. Ensure:

```bash
heroku stack:set container -a YOUR_APP_NAME
```

Then redeploy:

```bash
git push heroku main
```

If you still get 404, verify the Docker build completes (no frontend build failures in `heroku logs`).

### Option B: Buildpack Stack (May Not Run Node on Heroku-24)

If your app uses **buildpacks** (heroku-22, heroku-24), the frontend must be built by the Node.js buildpack before Python runs. Add the Node.js buildpack **first**:

```bash
heroku buildpacks:add --index 1 heroku/nodejs -a YOUR_APP_NAME
heroku buildpacks:add heroku/python -a YOUR_APP_NAME
heroku config:set NPM_CONFIG_PRODUCTION=false -a YOUR_APP_NAME
git push heroku main
```

**Note**: On Heroku-24, the build may run only the Python buildpack even when Node is listed first. If you still get 404 after redeploying, **switch to Container stack** (Option A) for a reliable fix.

### Verify Your Stack

```bash
heroku stack -a YOUR_APP_NAME
```

- `container` → Docker (Option A)
- `heroku-22` or similar → Buildpack (Option B)

### Verify Buildpacks (for buildpack apps)

```bash
heroku buildpacks -a YOUR_APP_NAME
```

You should see `heroku/nodejs` **before** `heroku/python`.
