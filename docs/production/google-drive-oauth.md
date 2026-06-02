# Production setup: Google Drive per-user OAuth for Open WebUI

This guide configures **per-user OAuth**: the admin sets integration once, then each Open WebUI user authorizes their own Google account one time.

## Scope and security model

- Uses official Open WebUI Google Drive integration flags.
- Uses end-user OAuth (not service accounts).
- Uses Google API access (not public link scraping).
- Access is limited to files each user can already access in their own Google account.

## 1) Prepare environment variables

Generate a stable secret once:

```bash
openssl rand -hex 32
```

Set these variables in your deployment environment (`.env` for Docker Compose):

- `WEBUI_SECRET_KEY` (required, stable after first production rollout)
- `ENABLE_GOOGLE_DRIVE_INTEGRATION=true`
- `GOOGLE_DRIVE_CLIENT_ID` (required)
- `GOOGLE_DRIVE_API_KEY` (required)

> Warning: do **not** rotate `WEBUI_SECRET_KEY` in production unless you intentionally invalidate encrypted OAuth/session tokens.

## 2) Google Cloud configuration (exact steps)

1. Create (or select) a Google Cloud project.
2. Enable APIs:
   - **Google Drive API**
   - **Google Picker API**
3. Configure OAuth consent screen:
   - User Type: Internal/External as required.
   - Add app name, support email, developer email.
   - Add your production domain in authorized domains if required by Google UI.
   - Add test users if app is in testing mode.
4. Create OAuth Client ID:
   - Type: **Web application**
   - Authorized JavaScript origins: `https://<your-openwebui-domain>`
   - Authorized redirect URI: `https://<your-openwebui-domain>/oauth/google/callback`
5. Create API key:
   - Restrict key to **Google Picker API** (and only required APIs).
   - Restrict HTTP referrers to your production Open WebUI origin (for example `https://<your-openwebui-domain>/*`) if your deployment pattern supports it.

## 3) Docker Compose wiring

In `docker-compose.yaml`, pass variables through to the `open-webui` service:

```yaml
environment:
  - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY:?WEBUI_SECRET_KEY is required}
  - ENABLE_GOOGLE_DRIVE_INTEGRATION=${ENABLE_GOOGLE_DRIVE_INTEGRATION:-true}
  - GOOGLE_DRIVE_CLIENT_ID=${GOOGLE_DRIVE_CLIENT_ID:?GOOGLE_DRIVE_CLIENT_ID is required}
  - GOOGLE_DRIVE_API_KEY=${GOOGLE_DRIVE_API_KEY:?GOOGLE_DRIVE_API_KEY is required}
```

## 4) Pre-deploy validation

Run before deployment:

```bash
./scripts/validate-google-drive-env.sh .env
```

- Fails if required vars are missing/empty.
- Warns if integration is disabled.
- Warns if `WEBUI_SECRET_KEY` looks like a placeholder.

## 5) Deploy/restart

```bash
docker compose up -d --force-recreate open-webui
```

## 6) Verification steps

1. Sign in to Open WebUI as a normal user.
2. Open attachment/file picker and choose Google Drive.
3. Complete Google authorization flow once for that user.
4. Select a Google Sheet the user can already access.
5. Ask Open WebUI to summarize the sheet.
6. Confirm:
   - access succeeds for permitted files,
   - access fails for files the user does not have permission to view.

## 7) Rollback

1. Disable integration:
   - `ENABLE_GOOGLE_DRIVE_INTEGRATION=false`
2. Recreate service:
   - `docker compose up -d --force-recreate open-webui`
3. Keep `WEBUI_SECRET_KEY` unchanged during rollback to avoid breaking existing encrypted token/session data.
