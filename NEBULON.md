# Nebulon AI branding fork

This repository is a private fork of [Open WebUI](https://github.com/open-webui/open-webui) (v0.13.x), deployed as **Nebulon AI** for an internal team (&lt;50 users). User-visible Open WebUI branding has been replaced per license clause 4(i). The upstream `LICENSE` file and required copyright notices in source remain unchanged.

## What we changed

| Area | Change |
|------|--------|
| Product name | Default `WEBUI_NAME` / `APP_NAME` → **Nebulon AI** (no `(Open WebUI)` suffix) |
| Version / community | `ENABLE_VERSION_UPDATE_CHECK` and `ENABLE_COMMUNITY_SHARING` default to **false**; upstream doc/discord/sponsor links removed from settings UI |
| i18n | Locale **values** (and English **keys** where they contained the old name) updated to Nebulon AI |
| Assets | Official pack **v1.1** in `static/brand/nebulon-ai-logo-v1.1/` (see pack `README.md`); legacy paths under `static/static/` via `scripts/install-nebulon-brand.sh` |

Python package name `open_webui` is unchanged.

## Official logo files

1. Drop a new pack under `static/brand/nebulon-ai-logo-v1.1/` (or set `NEBULON_BRAND_SRC` when running the installer).
2. Run: `bash scripts/install-nebulon-brand.sh`
3. Run `npm run build` so `build/` picks up assets.

The installer copies icons into legacy filenames (`favicon.png`, `splash.png`, PWA sizes, etc.) in `static/static/` and `backend/open_webui/static/`. Theme-aware favicons use `favicon-dark.*` when the UI is in dark mode (`src/app.html`, `src/lib/utils/theme.ts`).

UI wiring: `src/lib/branding.ts`, `src/lib/components/common/BrandMark.svelte` (auth, onboarding, sidebar).

## Environment variables

| Variable | Default in this fork | Notes |
|----------|----------------------|--------|
| `WEBUI_NAME` | `Nebulon AI` | Override if needed |
| `ENABLE_VERSION_UPDATE_CHECK` | `false` | Set `true` only if you want upstream update UI |
| `ENABLE_COMMUNITY_SHARING` | `false` | Open WebUI community publishing |

## Merging upstream Open WebUI

```bash
git remote add upstream https://github.com/open-webui/open-webui.git  # once
git fetch upstream
git merge upstream/main   # or the release tag you track
```

After each merge, re-apply or verify:

1. `backend/open_webui/env.py` — `WEBUI_NAME` default and suffix logic
2. `src/lib/constants.ts` — `APP_NAME`, `COMMUNITY_ORIGINS`
3. `backend/open_webui/config.py` — community/version feature defaults
4. i18n — run `python3 scripts/nebulon_i18n_rebrand.py` if new English strings mention Open WebUI
5. Brand assets under the three static directories listed above
6. Settings/About, admin General, `UserMenu.svelte`, onboarding — upstream may re-add community links
7. `NEBULON.md` and this checklist

Helper scripts (optional):

- `scripts/nebulon_i18n_rebrand.py`
- `scripts/nebulon_source_rebrand.py` (skips copyright/LICENSE comment lines)
- `scripts/nebulon_brand_assets.py` (regenerate placeholder PNGs; requires Pillow)

## Railway / Docker

Build from repo root with the root `Dockerfile`. The app listens on **port 8080**.