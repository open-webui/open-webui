# Deploy Open WebUI to Fly.io (Fly Postgres + OpenRouter)

This guide uses a Fly app named `open-webui-26z5ca` in region `sin` and Fly Postgres for production.

## 1) Authenticate and create app

```bash
fly auth login
fly apps create open-webui-26z5ca
```

## 2) Create Fly Postgres and attach it

```bash
fly postgres create --name yh-openwebui-db --region sin
fly postgres attach --app open-webui-26z5ca yh-openwebui-db
```

## 3) Configure OpenRouter + production secrets

```bash
fly secrets set OPENAI_API_BASE_URL="https://openrouter.ai/api/v1" --app open-webui-26z5ca
fly secrets set OPENAI_API_KEY="YOUR_OPENROUTER_API_KEY" --app open-webui-26z5ca
fly secrets set ENABLE_SIGNUP="False" --app open-webui-26z5ca
fly secrets set WEBUI_SECRET_KEY="<generate-long-random-secret>" --app open-webui-26z5ca
```

## 4) Create persistent runtime volume (required before first deploy)

Run this once before the first production deploy so `/app/backend/data` is durable across restarts/redeploys:

```bash
fly volumes create openwebui_data --region sin --size 5 --app open-webui-26z5ca
```

## 5) Deploy and open

```bash
fly deploy --app open-webui-26z5ca
fly open --app open-webui-26z5ca
```

## Build strategy

This Fly deployment builds from the repository `Dockerfile` declared in `fly.toml`. The repository build is required so the deployed image includes custom Open WebUI source changes, including Team Workspace V1 backend routes, models, and frontend UI.

The Dockerfile builds the frontend from the checked-out repository source and copies `./backend` into the runtime image, so custom files are included in the final Fly image.

## Troubleshooting

If deployment fails with `app not found`, verify the Fly app name in `fly.toml`, `.github/workflows/fly-deploy.yml`, and all manual `fly` commands matches the actual app shown by:

```bash
fly apps list
```

If build fails with `JavaScript heap out of memory`, keep `fly.toml` pointed at `Dockerfile` and adjust the repository build resources or Node build settings. Do not switch Fly back to an upstream prebuilt image, because that would omit repository customizations from production.

## Notes

- This setup is deployment-focused and intentionally deploys this repository's customized Open WebUI source code.
- Do not use SQLite for production; Fly Postgres is attached in step 2.
- Fly Postgres persists database state.
- The Fly volume persists `/app/backend/data` runtime data.
- Do not delete the volume unless you intentionally want to reset app runtime data.
- Keep `WEBUI_SECRET_KEY` long and random.
