# Deploy Open WebUI to Fly.io (Fly Postgres + OpenRouter)

This guide uses a Fly app named `yh-openwebui` in region `sin` and Fly Postgres for production.

## 1) Authenticate and create app

```bash
fly auth login
fly apps create yh-openwebui
```

## 2) Create Fly Postgres and attach it

```bash
fly postgres create --name yh-openwebui-db --region sin
fly postgres attach --app yh-openwebui yh-openwebui-db
```

## 3) Configure OpenRouter + production secrets

```bash
fly secrets set OPENAI_API_BASE_URL="https://openrouter.ai/api/v1" --app yh-openwebui
fly secrets set OPENAI_API_KEY="YOUR_OPENROUTER_API_KEY" --app yh-openwebui
fly secrets set ENABLE_SIGNUP="False" --app yh-openwebui
fly secrets set WEBUI_SECRET_KEY="<generate-long-random-secret>" --app yh-openwebui
```

## 4) Create persistent runtime volume (required before first deploy)

Run this once before the first production deploy so `/app/backend/data` is durable across restarts/redeploys:

```bash
fly volumes create openwebui_data --region sin --size 5 --app yh-openwebui
```

## 5) Deploy and open

```bash
fly deploy --app yh-openwebui
fly open --app yh-openwebui
```

## Notes

- This setup is deployment-focused and does not modify upstream Open WebUI application source code.
- Do not use SQLite for production; Fly Postgres is attached in step 2.
- Fly Postgres persists database state.
- The Fly volume persists `/app/backend/data` runtime data.
- Do not delete the volume unless you intentionally want to reset app runtime data.
- Keep `WEBUI_SECRET_KEY` long and random.
