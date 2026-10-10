# Theme and branding specification

## Summary

Theme the fork with CSS variables in `static/static/custom.css`, which upstream already loads, and have the new components read those variables instead of fixed colors.

## Goals

- One set of tokens drives light and dark modes.
- Accent, mode default, app name and logo are editable on the Theme and branding screen.
- Respect the license's branding clause ([ADR 0001](../adr/0001-fork-open-webui-at-v0-11-4.md)).

## Design

Observed in the v0.11.4 source on 2026-10-09:

- `src/app.html` links `/static/custom.css` (line 39) and `/static/favicon.png` (line 9).
- `static/static/custom.css` exists and is empty.
- `WEBUI_NAME` (in `backend/open_webui/env.py`) appends ` (Open WebUI)` when overridden.
- Logo and icon files live in `static/static/` (`logo.png`, `favicon.png`, `favicon.svg`, `favicon.ico`, `favicon-96x96.png`, `apple-touch-icon.png`, splash images and web-app manifests).
- `static/BRANDING.md` says not to alter or remove Open WebUI branding except as the license permits.

### Tokens

| Token | Light | Dark |
| --- | --- | --- |
| `--cw-accent` | `#0F6B5C` | the accent mixed 55% with white, so buttons keep contrast |
| `--cw-ground` | `#F4F5F2` | `#111A17` |
| `--cw-surface` | `#FFFFFF` | `#1A2622` |
| `--cw-ink` | `#16201D` | `#E6EBE7` |
| `--cw-radius` | `12px` | `12px` |

### Mechanics

1. Define the tokens at `:root` and override them under the `dark` class in `custom.css`. Upstream sets a `dark` or `light` class on the root element from the saved theme choice.
2. Build every new component from the tokens, for example `bg-[var(--cw-accent)]`, so a theme change never touches component code.
3. The Theme and branding screen saves accent, default mode, app name and logo to the `cowork_setting` table (key `theme`). A backend route serves them as generated CSS that loads after `custom.css`.
4. Logo and favicon are files under `static/static/`.

### License limit

Changing the app name or replacing the logo is allowed only when the deployment has 50 or fewer end users in a rolling 30 days, written permission exists, or an enterprise license is held. Until that is confirmed, leave the protected Open WebUI name and logo in place and theme colors only.

## Open questions

- Will the instance ever exceed 50 end users? This decides whether name and logo changes are allowed.
- Does the generated-CSS route need caching, and how does it invalidate when settings change?

## Related docs

- [Frontend components](frontend-components.md)
