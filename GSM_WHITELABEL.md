# GSM White-Label Reference Guide

This document tracks all customizations made to white-label Open WebUI as **GSM**.
Use this as a checklist when merging new upstream releases.

---

## Quick Merge Workflow

```bash
# 1. Sync fork's master with upstream (GitHub UI: "Sync fork" button)
# 2. Or manually:
git fetch upstream main
git checkout master
git merge upstream/main

# 3. Merge into your GSM branch
git checkout gsm-branding
git merge master

# 4. Resolve conflicts using this file as reference
# 5. Verify branding is intact
grep -r "Open WebUI" src/ backend/ --include="*.svelte" --include="*.py" --include="*.ts" --include="*.html" -l
```

---

## Files Modified for GSM Branding

### 1. Core Constants & Configuration

| File | Change |
|---|---|
| `src/lib/constants.ts` | `APP_NAME = 'GSM'` |
| `backend/open_webui/env.py` | `WEBUI_NAME = "GSM"`, `WEBUI_FAVICON_URL = "/static/favicon.png"` |

### 2. HTML & Meta Tags

| File | Change |
|---|---|
| `src/app.html` | `<title>GSM</title>` |

### 3. Logo & Icon Files (Replace with GSM assets)

**Frontend static:**
| File | Size/Format |
|---|---|
| `static/static/favicon.png` | 512x512 PNG |
| `static/static/favicon-96x96.png` | 96x96 PNG |
| `static/static/favicon-dark.png` | 512x512 PNG (dark variant) |
| `static/static/favicon.svg` | SVG |
| `static/static/favicon.ico` | 64x64 ICO |
| `static/static/apple-touch-icon.png` | 180x180 PNG |
| `static/static/logo.png` | 200x200 PNG |
| `static/static/splash.png` | 400x400 PNG (light) |
| `static/static/splash-dark.png` | 400x400 PNG (dark) |
| `static/static/web-app-manifest-192x192.png` | 192x192 PNG |
| `static/static/web-app-manifest-512x512.png` | 512x512 PNG |

**Backend static (mirrors of frontend):**
| File | Size/Format |
|---|---|
| `backend/open_webui/static/favicon.png` | 512x512 PNG |
| `backend/open_webui/static/favicon-96x96.png` | 96x96 PNG |
| `backend/open_webui/static/favicon-dark.png` | 512x512 PNG |
| `backend/open_webui/static/favicon.svg` | SVG |
| `backend/open_webui/static/favicon.ico` | 64x64 ICO |
| `backend/open_webui/static/apple-touch-icon.png` | 180x180 PNG |
| `backend/open_webui/static/logo.png` | 200x200 PNG |
| `backend/open_webui/static/splash.png` | light splash |
| `backend/open_webui/static/splash-dark.png` | dark splash |

### 4. PWA Manifest

| File | Change |
|---|---|
| `backend/open_webui/static/site.webmanifest` | `"name": "GSM"`, `"short_name": "GSM"` |

### 5. Svelte Components (Text Replacements)

These files had hardcoded "Open WebUI" replaced with "GSM":

| File | What Changed |
|---|---|
| `src/lib/components/chat/Settings/About.svelte` | Rebranded About page, removed community links, GSM copyright |
| `src/lib/components/chat/Settings/General.svelte` | "Help us translate GSM!" |
| `src/lib/components/channel/Channel.svelte` | Page title `• GSM` |
| `src/routes/+layout.svelte` | Notification text `• GSM` |
| `src/lib/components/admin/Settings/General.svelte` | Admin settings text |
| `src/lib/components/admin/Settings/Audio.svelte` | Audio settings text |
| `src/lib/components/admin/Functions.svelte` | Functions page text |
| `src/lib/components/admin/Users/UserList.svelte` | Users page text |
| `src/lib/components/admin/Evaluations/Feedbacks.svelte` | Feedbacks text |
| `src/lib/components/chat/Settings/Connections.svelte` | CORS message |
| `src/lib/components/chat/Settings/Integrations.svelte` | CORS message |
| `src/lib/components/chat/Settings/SyncStatsModal.svelte` | Sync stats text |
| `src/lib/components/chat/ShareChatModal.svelte` | Share modal text |
| `src/lib/components/chat/ToolServersModal.svelte` | Tool servers text |
| `src/lib/components/chat/XTerminal.svelte` | Terminal comments |
| `src/lib/components/workspace/Models.svelte` | Models page text |
| `src/lib/components/workspace/Prompts.svelte` | Prompts page text |
| `src/lib/components/workspace/Tools.svelte` | Tools page text |
| `src/lib/components/workspace/common/ManifestModal.svelte` | Manifest modal text |
| `src/lib/components/AddToolServerModal.svelte` | MCP support text |
| `src/routes/(app)/admin/functions/create/+page.svelte` | Version check message |
| `src/routes/(app)/admin/functions/edit/+page.svelte` | Version check message |
| `src/routes/(app)/workspace/tools/create/+page.svelte` | Version check message |
| `src/routes/(app)/workspace/tools/edit/+page.svelte` | Version check message |

### 6. Translation Files (All Locales)

All `src/lib/i18n/locales/*/translation.json` files had "Open WebUI" replaced with "GSM" in translation keys. This affects ~50 locale files.

**Key translation keys changed:**
- `"CORS must be properly configured by the provider to allow requests from GSM."`
- `"Discover how to use GSM and seek support from the community."`
- `"Do you want to sync your usage stats with GSM Community?"`
- `"Made by GSM Community"`
- `"GSM can use tools provided by any OpenAPI server."`
- `"GSM uses faster-whisper internally."`
- `"GSM uses SpeechT5 and CMU Arctic speaker embeddings."`
- `"GSM version"`
- `"GSM version (v{{OPEN_WEBUI_VERSION}}) is lower than required version (v{{REQUIRED_VERSION}})"`
- `"Redirecting you to GSM Community"`
- `"Share to GSM Community"`

### 7. Backend Python Files

These files had "Open WebUI" replaced with "GSM" in user-facing strings:

| File | What Changed |
|---|---|
| `backend/open_webui/__init__.py` | Package description |
| `backend/open_webui/config.py` | Config descriptions |
| `backend/open_webui/main.py` | API title/description |
| `backend/open_webui/routers/ollama.py` | User-Agent header |
| `backend/open_webui/routers/openai.py` | User-Agent header |
| `backend/open_webui/routers/audio.py` | Audio router text |
| `backend/open_webui/routers/scim.py` | SCIM router text |
| `backend/open_webui/tools/__init__.py` | Tools text |
| `backend/open_webui/tools/builtin.py` | Built-in tools text |
| `backend/open_webui/utils/oauth.py` | OAuth text |
| `backend/open_webui/utils/telemetry/metrics.py` | Telemetry text |
| `backend/open_webui/retrieval/loaders/external_web.py` | Loader text |
| `backend/open_webui/retrieval/vector/dbs/milvus_multitenancy.py` | DB text |
| `backend/open_webui/retrieval/vector/dbs/pgvector.py` | DB text |
| `backend/open_webui/retrieval/vector/dbs/qdrant_multitenancy.py` | DB text |
| `backend/open_webui/retrieval/vector/dbs/s3vector.py` | DB text |
| `backend/open_webui/retrieval/web/azure.py` | Web search text |
| `backend/open_webui/retrieval/web/external.py` | Web search text |
| `backend/open_webui/retrieval/web/searxng.py` | Web search text |
| `backend/open_webui/retrieval/web/yacy.py` | Web search text |
| `backend/open_webui/retrieval/web/yandex.py` | Web search text |

---

## Conflict Resolution Tips

When merging upstream updates, conflicts will most likely occur in:

1. **`src/app.html`** - Restore `<title>GSM</title>`
2. **`backend/open_webui/env.py`** - Keep `WEBUI_NAME = "GSM"` and `WEBUI_FAVICON_URL = "/static/favicon.png"`
3. **`src/lib/components/chat/Settings/About.svelte`** - Keep GSM branding, copyright
4. **`backend/open_webui/static/site.webmanifest`** - Keep `"name": "GSM"`
5. **Image files** - Keep GSM logo files (upstream will try to restore their logos)
6. **New files from upstream** - Check for any new "Open WebUI" references in newly added components

### Post-Merge Verification

After every merge, run this command to find any missed "Open WebUI" references:

```bash
# Check frontend
grep -r "Open WebUI" src/ --include="*.svelte" --include="*.ts" --include="*.html" -l

# Check backend
grep -r "Open WebUI" backend/ --include="*.py" -l

# Check translations (only en-US is sufficient)
grep "Open WebUI" src/lib/i18n/locales/en-US/translation.json
```

---

## Regenerating Logo Files

If you need to regenerate the GSM logo assets (e.g., with a new design), use a Python script with Pillow or provide new image files and copy them to both:
- `static/static/` (frontend)
- `backend/open_webui/static/` (backend mirror)

Ensure you generate all required sizes listed in section 3 above.
