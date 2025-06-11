# Delta Report - Rebrand Phase 2: Name Fix + Artifacts + Frontend Stubs

This report summarizes the changes made during this phase of the rebranding effort.

## I. Files Added/Modified

### New Files Created:
- `TASKS.md`
- `.windsurfrules`
- `patches/brace-expansion+2.0.2.patch` (placeholder content)
- `src/app/(main)/chat/page.tsx`
- `src/app/(main)/history/page.tsx`
- `src/app/(main)/settings/page.tsx`
- `src/app/(main)/usage/page.tsx`
- *Pending: `.github/workflows/ci.yml`*

### Existing Files Modified:
- `branding-map.md` (Brand name updated: "TechSecAI Hub" -> "TechSci AI Hub" and other variants)
- `backend/open_webui/routers/ollama.py` (Global brand name correction for headers and error messages via overwrite: "TechSecAI Hub" -> "TechSci AI Hub", "X-TechSecAI-Hub-*" -> "X-TechSci-AI-Hub-*", etc.)
- `backend/open_webui/config.py` (Brand name corrections like `TECHSECAI_HUB_DIR` -> `TECHSCI_AI_HUB_DIR`, `techsecai-hub` slugs to `techsci-ai-hub`, TODOs for API URLs)
- `backend/open_webui/env.py` (Brand name corrections like `TECHSECAI_HUB_DIR` -> `TECHSCI_AI_HUB_DIR`, `WEBUI_NAME` to "TechSci AI Hub", package names to `techsci-ai-hub`, `OTEL_SERVICE_NAME` to `techsci-ai-hub`, zip file name to `techsci_ai_hub_data`, TODO for favicon URL)
- `backend/open_webui/main.py` (FastAPI `title` to "TechSci AI Hub", `description`, `license_info`, `contact` updated with "TechSci AI Hub" and TODOs. ASCII art updated. GitHub URL for releases updated. TODO for manifest description.)
- `backend/open_webui/retrieval/loaders/external_web.py` (User-Agent updated from "TechSecAI Hub Agent" to "TechSci AI Hub Agent" and repo path in URL)
- `backend/open_webui/retrieval/loaders/mistral.py` (User-Agent updated from "TechSecAIHub-MistralLoader" to "TechSciAIHub-MistralLoader")
- `backend/open_webui/retrieval/utils.py` (HTTP headers updated from `X-TechSecAI-Hub-*` to `X-TechSci-AI-Hub-*`)
- `backend/open_webui/routers/audio.py` (HTTP headers updated from `X-TechSecAI-Hub-*` to `X-TechSci-AI-Hub-*`; error messages from "TechSecAI Hub" to "TechSci AI Hub")
- `backend/open_webui/routers/files.py` (HTTP headers updated from `TechSecAI-Hub-*` to `TechSci-AI-Hub-*`)
- `backend/open_webui/routers/images.py` (HTTP headers updated from `X-TechSecAI-Hub-*` to `X-TechSci-AI-Hub-*`)
- `backend/open_webui/test/apps/webui/routers/test_auths.py` (Test email domains updated from `@techsecaihub.com` to `@techsciaihub.com`)
- `backend/open_webui/test/apps/webui/routers/test_users.py` (Test email domains updated from `@techsecaihub.com` to `@techsciaihub.com`)
- `package.json` (Added `patch-package` script and devDependency)
- *Note: GitHub workflow files (.github/) were assumed to be corrected by earlier broad script actions for "Open WebUI" -> "TechSci AI Hub" and were not explicitly part of the "TechSecAI Hub" -> "TechSci AI Hub" correction pass in this subtask list.*

## II. Remaining License-Sensitive & Branding Items (`requires-rewrite`)

The following items, primarily sourced from `branding-map.md` (which now reflects the "TechSci AI Hub" target name where applicable, but original "Open WebUI" for tasks), require manual review, rewriting, or external asset/URL provisioning. `TODO: Rebrand [TechSci AI Hub]: ...` comments have been inserted in code where these occur and were part of the file modifications.

*   **Legal Documents:**
    *   `CONTRIBUTOR_LICENSE_AGREEMENT`: Title and all mentions of "Open WebUI".
    *   License name and URL in `backend/open_webui/main.py`'s FastAPI definition (currently has placeholder and TODO).
    *   References to the "Open WebUI License" in `README.md`.
*   **External URLs:**
    *   All links to `docs.openwebui.com` (e.g., in `README.md`, `.github/pull_request_template.md` - though this specific GH file was likely fixed by earlier scripts).
    *   All links to `openwebui.com` (e.g., in `README.md`, `backend/open_webui/env.py` `WEBUI_FAVICON_URL`).
    *   API URLs in `backend/open_webui/config.py` pointing to `api.openwebui.com`.
    *   Referer URL in `backend/open_webui/routers/openai.py`.
*   **Asset Content:**
    *   All image assets listed in `branding-map.md` (logos, favicons, splash screens) require new "TechSci AI Hub" versions.
    *   Shield badge URLs and Star History chart URLs in `README.md` need to point to the new repository and reflect new stats.
    *   Sponsor logos in `README.md` are for the old brand.
*   **Contact Information:**
    *   Author email in `pyproject.toml` (`tim@openwebui.com`).
    *   Reporting email in `CODE_OF_CONDUCT.md` (`hello@openwebui.com`).
    *   Sales email in `README.md` (`sales@openwebui.com`).
    *   Contact email in `backend/open_webui/main.py` (currently placeholder with TODO).
*   **Core Code/Component Identifiers (Potentially Svelte-related):**
    *   Any Svelte component names like `OpenWebUIModal.svelte` if they exist and are planned for conversion/review. The `branding-map.md` would list these; tasks generated from these need re-evaluation based on Next.js migration.
*   **Manifest Files (`site.webmanifest`, `manifest.json`, `opensearch.xml`):** While textual names were auto-replaced (e.g. "Open WebUI" to "TechSci AI Hub"), icons and potentially other fields linked to assets need review once new assets are available. The description in `main.py` for `manifest.json` has a TODO.

## III. Blockers or Questions

*   **Resolved Blocker (ollama.py):** Initial difficulty modifying `backend/open_webui/routers/ollama.py` using diff-based patching was overcome by using a file overwrite strategy for that specific file during the "TechSecAI Hub" -> "TechSci AI Hub" correction phase.
*   **Frontend Tech Stack Shift:** The project is now proceeding with a Next.js/React (TSX) frontend. The original codebase contains a Svelte frontend. Tasks in `TASKS.md` derived from Svelte files (e.g. `src/lib/...` paths in `branding-map.md`) need to be re-evaluated: items in Svelte files might be rebranded during conversion to Next.js, or the Svelte files might be removed entirely, making some specific branding tasks for them obsolete. This needs clarification.
*   **New Assets Required:** New visual assets (logos, favicons, splash screens, etc.) for "TechSci AI Hub" are needed to replace the old ones. The `branding-map.md` lists original assets.
*   **Target URLs Needed:** The new URLs for documentation, community sites, and support/contact channels are required to update the `TODO` items for links (currently placeholders like `docs.example.com` were used in some places).
*   **`brace-expansion@2.0.2.patch` Content:** The actual diff content for this security patch is still pending and needs to be added to `patches/brace-expansion+2.0.2.patch`.
