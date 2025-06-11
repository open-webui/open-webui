# Branding Inventory Map

This document lists all identified "Open WebUI", "OpenWebUI", and "open-webui" brand references within the codebase.

## Textual References

| File Path | Line Number(s) | Context / Text Snippet | Category (`auto-replace` / `requires-rewrite`) | Notes |
|---|---|---|---|---|
| .github/ISSUE_TEMPLATE/bug_report.yaml | 2 | description: Create a detailed bug report to help us improve Open WebUI. | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 16 | - **Respectful collaboration**: Open WebUI is a volunteer-driven project... | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 18 | ...to maintain Open WebUI's quality. | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 30 | - label: I am using the latest version of Open WebUI. | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 37 | description: How did you install Open WebUI? | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 49 | label: Open WebUI Version | `auto-replace` | Form label |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 86 | - label: I am using the latest version of **both** Open WebUI and Ollama. | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 134 | 3. Clone the Open WebUI repo (git clone ...). | `auto-replace` | Instructional text |
| .github/ISSUE_TEMPLATE/bug_report.yaml | 167 | Thank you for contributing to Open WebUI! | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/feature_request.yaml | 19 | - Open WebUI is a **volunteer-driven project** | `auto-replace` | General text |
| .github/ISSUE_TEMPLATE/feature_request.yaml | 27 | ...quality and continuity of Open WebUI. | `auto-replace` | General text |
| .github/pull_request_template.md | 10 | - [ ] **Documentation:** Have you updated relevant documentation [Open WebUI Docs](https://github.com/open-webui/docs)... | `auto-replace` | Link text & URL |
| .github/workflows/deploy-to-hf-spaces.yml | 40 | echo "title: Open WebUI" >> temp_readme.md | `auto-replace` | Text in script |
| CONTRIBUTOR_LICENSE_AGREEMENT | 1 | # Open WebUI Contributor License Agreement | `requires-rewrite` | Legal document title |
| CONTRIBUTOR_LICENSE_AGREEMENT | 3 | This Open WebUI Contributor License Agreement ("Agreement") is made and entered into by and between Open WebUI ("Licensor")... | `requires-rewrite` | Legal document content |
| README.md | 1 | # Open WebUI 👋 | `auto-replace` | Main project title |
| README.md | 13 | TechSecAI Hub is an [extensible](https://docs.openwebui.com/features/plugin/), feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline. (Note: "TechSecAI Hub" seems to be a new name being introduced, mixed with "Open WebUI" references) | `requires-rewrite` | Project description, mixed branding |
| README.md | 18 | > **Looking for an [Enterprise Plan](https://docs.openwebui.com/enterprise)?** – **[Speak with Our Sales Team Today!](mailto:sales@openwebui.com)** (References openwebui.com) | `requires-rewrite` | Link to old docs/sales |
| README.md | 22 | For more information, be sure to check out our [TechSecAI Hub Documentation](https://docs.openwebui.com/). (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 40 | ...import models effortlessly through [TechSecAI Hub Community](https://openwebui.com/) integration. (References openwebui.com) | `requires-rewrite` | Link to old community site |
| README.md | 62 | Want to learn more about TechSecAI Hub's features? Check out our [TechSecAI Hub documentation](https://docs.openwebui.com/features) for a comprehensive overview! (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 130 | ...our detailed guide on [TechSecAI Hub Documentation](https://docs.openwebui.com/) is ready to assist you. (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 192 | Visit our [TechSecAI Hub Documentation](https://docs.openwebui.com/getting-started/) or join our [Discord community](https://discord.gg/5rJgQTnV4s) for comprehensive guidance. (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 194 | Look at the [Local Development Guide](https://docs.openwebui.com/getting-started/advanced-topics/development) for instructions... (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 198 | Encountering connection issues? Our [TechSecAI Hub Documentation](https://docs.openwebui.com/troubleshooting/) has got you covered. (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 220 | Check our Updating Guide available in our [TechSecAI Hub Documentation](https://docs.openwebui.com/getting-started/updating). (References openwebui.com) | `requires-rewrite` | Link to old docs |
| README.md | 243 | Discover upcoming features on our roadmap in the [TechSecAI Hub Documentation](https://docs.openwebui.com/roadmap/). (References openwebui.com) | `requires-rewrite` | Link to old docs |
| backend/open_webui/config.py | 687 | r = requests.get(f"https://api.openwebui.com/api/v1/custom/{CUSTOM_NAME}") | `requires-rewrite` | API URL |
| backend/open_webui/config.py | 692 | f"https://api.openwebui.com{data['logo']}" | `requires-rewrite` | API URL for logo |
| backend/open_webui/config.py | 705 | f"https://api.openwebui.com{data['splash']}" | `requires-rewrite` | API URL for splash |
| backend/open_webui/env.py | 113 | WEBUI_FAVICON_URL = "https://openwebui.com/favicon.png" | `requires-rewrite` | URL for favicon asset |
| backend/open_webui/main.py | 27 | title="Open WebUI", | `auto-replace` | FastAPI app title |
| backend/open_webui/main.py | 28 | description="An open-source WebUI for LLMs.", | `auto-replace` | FastAPI app description |
| backend/open_webui/main.py | 29 | version=WEBUI_VERSION, | `auto-replace` | Version string (indirect) |
| backend/open_webui/main.py | 30 | license_info={ | `auto-replace` | License info (indirect) |
| backend/open_webui/main.py | 31 | "name": "Open WebUI License", | `requires-rewrite` | License name |
| backend/open_webui/main.py | 32 | "url": "https://docs.openwebui.com/license/", | `requires-rewrite` | License URL |
| backend/open_webui/main.py | 1603 | "https://api.github.com/repos/open-webui/open-webui/releases/latest", | `auto-replace` | GitHub API URL |
| backend/open_webui/retrieval/loaders/external_web.py | 35 | "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) External Web Loader", | `auto-replace` | User-Agent string |
| backend/open_webui/retrieval/loaders/mistral.py | 88 | "User-Agent": "OpenWebUI-MistralLoader/2.0", | `auto-replace` | User-Agent string |
| backend/open_webui/retrieval/utils.py | Multiple | "X-OpenWebUI-User-Name", "X-OpenWebUI-User-Id", etc. | `auto-replace` | Custom HTTP headers |
| backend/open_webui/routers/audio.py | Multiple | "X-OpenWebUI-User-Name", "X-OpenWebUI-User-Id", etc. | `auto-replace` | Custom HTTP headers |
| backend/open_webui/routers/files.py | Multiple | "OpenWebUI-User-Email", "OpenWebUI-User-Id", etc. | `auto-replace` | Custom HTTP headers |
| backend/open_webui/routers/images.py | Multiple | "X-OpenWebUI-User-Name", "X-OpenWebUI-User-Id", etc. | `auto-replace` | Custom HTTP headers |
| backend/open_webui/routers/ollama.py | Multiple | "X-OpenWebUI-User-Name", "X-OpenWebUI-User-Id", etc. | `auto-replace` | Custom HTTP headers |
| backend/open_webui/routers/openai.py | 220 | "HTTP-Referer": "https://openwebui.com/", | `requires-rewrite` | Referer URL |
| backend/open_webui/test/apps/webui/routers/test_auths.py | Multiple | "john.doe@openwebui.com" | `auto-replace` | Test email addresses |
| backend/open_webui/test/apps/webui/routers/test_users.py | Multiple | "user{id}@openwebui.com" | `auto-replace` | Test email addresses |
| docs/src/pages/index.mdx | 3 | title: Open WebUI Documentation | `auto-replace` | Docs page title |
| docs/src/pages/index.mdx | 7 | Welcome to the official Open WebUI documentation. | `auto-replace` | Docs intro text |
| kubernetes/manifest/base/webui-deployment.yaml | 18 | image: ghcr.io/open-webui/open-webui:main | `auto-replace` | Docker image name |
| package.json | 3 | "name": "open-webui", | `auto-replace` | NPM package name |
| package.json | 4 | "version": "1.3.1", | `auto-replace` | Version (indirect) |
| package.json | 5 | "description": "User-friendly WebUI for LLMs (Formerly Ollama WebUI)", | `auto-replace` | Package description |
| pyproject.toml | 2 | name = "open-webui" | `auto-replace` | Python package name |
| pyproject.toml | 3 | version = "0.1.124" | `auto-replace` | Version (indirect) |
| pyproject.toml | 4 | description = "Open WebUI is a user-friendly WebUI for LLMs." | `auto-replace` | Package description |
| pyproject.toml | 5 | { name = "Timothy Jaeryang Baek", email = "tim@openwebui.com" } | `requires-rewrite` | Author email |
| run.sh | 3 | image_name="open-webui" | `auto-replace` | Shell variable |
| run.sh | 4 | container_name="open-webui" | `auto-replace` | Shell variable |
| src/app.html | 7 | <title>Open WebUI</title> | `auto-replace` | HTML Title |
| src/lib/apis/custom/index.ts | 13 | const CUSTOM_API_BASE_URL = `${OPEN_WEBUI_BASE_URL}/api/v1/custom`; | `auto-replace` | API endpoint construction |
| src/lib/components/admin/Settings/General.svelte | Multiple | References to "Open WebUI" for version, links to docs.openwebui.com, github.com/open-webui | Mix of `auto-replace` and `requires-rewrite` | UI text and links |
| src/lib/constants.ts | 10 | export const APP_NAME = 'Open WebUI'; | `auto-replace` | Constant |
| src/lib/constants.ts | 14 | export const WEBUI_BASE_URL = PUBLIC_WEBUI_URL || 'https://openwebui.com'; | `requires-rewrite` | Default base URL |
| src/lib/i18n/locales/*/*.json | Multiple | "Open WebUI", "OpenWebUI" | `auto-replace` | Localization strings |
| src/routes/(app)/admin/functions/create/+page.svelte | Multiple | 'Open WebUI version ...' | `auto-replace` | UI text |
| src/routes/+layout.svelte | Multiple | Notification title `... • Open WebUI` | `auto-replace` | Notification text |
| static/opensearch.xml | 3 | <ShortName>Open WebUI</ShortName> | `auto-replace` | XML content |
| static/opensearch.xml | 5 | <Description>Search Open WebUI models and conversations</Description> | `auto-replace` | XML content |
| static/opensearch.xml | 7 | <Image height="16" width="16" type="image/x-icon">/favicon.ico</Image> | `auto-replace` | Path to asset (relative) |
| static/static/site.webmanifest | 2 | "name": "Open WebUI", | `auto-replace` | Webmanifest content |
| static/static/site.webmanifest | 3 | "short_name": "Open WebUI", | `auto-replace` | Webmanifest content |
| TROUBLESHOOTING.md | Multiple | ghcr.io/open-webui/open-webui:main, open-webui (volume name) | `auto-replace` | Docker image & volume names |
| ... many more from grep results ... | | | |

## Image & Asset References (Filenames & Paths)

| File Path | Original Asset Name | Category (`auto-replace` / `requires-rewrite`) | Notes (e.g., dimensions, type) |
|---|---|---|---|
| backend/open_webui/static/apple-touch-icon.png | apple-touch-icon.png | `auto-replace` | PNG |
| backend/open_webui/static/favicon-96x96.png | favicon-96x96.png | `auto-replace` | PNG |
| backend/open_webui/static/favicon-dark.png | favicon-dark.png | `auto-replace` | PNG, for dark themes |
| backend/open_webui/static/favicon.ico | favicon.ico | `auto-replace` | ICO |
| backend/open_webui/static/favicon.png | favicon.png | `auto-replace` | PNG |
| backend/open_webui/static/favicon.svg | favicon.svg | `auto-replace` | SVG |
| backend/open_webui/static/logo.png | logo.png | `auto-replace` | PNG, Primary Logo |
| backend/open_webui/static/site.webmanifest | site.webmanifest | `requires-rewrite` | JSON, check content for name/short_name |
| backend/open_webui/static/splash-dark.png | splash-dark.png | `auto-replace` | PNG, Splash screen for dark mode |
| backend/open_webui/static/splash.png | splash.png | `auto-replace` | PNG, Splash screen |
| static/favicon.png | favicon.png | `auto-replace` | PNG |
| static/manifest.json | manifest.json | `requires-rewrite` | JSON, similar to site.webmanifest |
| static/opensearch.xml | opensearch.xml | `requires-rewrite` | XML, check content for name/description |
| static/static/apple-touch-icon.png | apple-touch-icon.png | `auto-replace` | PNG |
| static/static/favicon-96x96.png | favicon-96x96.png | `auto-replace` | PNG |
| static/static/favicon-dark.png | favicon-dark.png | `auto-replace` | PNG |
| static/static/favicon.ico | favicon.ico | `auto-replace` | ICO |
| static/static/favicon.png | favicon.png | `auto-replace` | PNG |
| static/static/favicon.svg | favicon.svg | `auto-replace` | SVG |
| static/static/site.webmanifest | site.webmanifest | `requires-rewrite` | JSON, check content for name/short_name |
| static/static/splash-dark.png | splash-dark.png | `auto-replace` | PNG |
| static/static/splash.png | splash.png | `auto-replace` | PNG |
| README.md | `https://img.shields.io/github/stars/open-webui/open-webui?style=social` | `requires-rewrite` | Shield badge URL |
| README.md | `https://api.star-history.com/svg?repos=open-webui/open-webui...` | `requires-rewrite` | Star history chart URL |
| README.md | `https://docs.openwebui.com/sponsors/logos/n8n.png` | `requires-rewrite` | Sponsor logo URL (external) |
| README.md | `https://docs.openwebui.com/sponsors/logos/warp.png` | `requires-rewrite` | Sponsor logo URL (external) |
| README.md | `https://docs.openwebui.com/sponsors/logos/tailscale.png` | `requires-rewrite` | Sponsor logo URL (external) |

## CSS Variables & Component Names

| File Path | Item Name (Variable/Component) | Category (`auto-replace` / `requires-rewrite`) | Notes |
|---|---|---|---|
| backend/open_webui/env.py | `OTEL_SERVICE_NAME = "open-webui"` | `auto-replace` | Environment variable for OpenTelemetry |
| kubernetes/manifest/base/* | Various `open-webui` names for services, deployments, namespaces | `auto-replace` | Kubernetes resource names |
| backend/open_webui/config.py | `redis_key = f"open-webui:config:{key}"` | `auto-replace` | Redis key prefix |
| backend/open_webui/config.py | `PINECONE_INDEX_NAME = "open-webui-index"` | `auto-replace` | Pinecone index name |
| backend/open_webui/retrieval/vector/dbs/*.py | `self.collection_prefix = "open-webui"` | `auto-replace` | Vector DB collection prefix |
| backend/open_webui/socket/main.py | `"open-webui:session_pool"`, etc. | `auto-replace` | Redis pool names |
| (Anticipated) src/lib/components/OpenWebUIModal.svelte | OpenWebUIModal (example) | `requires-rewrite` | If such components exist, rename carefully |
| (Anticipated) src/app.css | `--owui-primary` (example) | `auto-replace` | If such CSS variables exist |

## URLs & Links

| File Path | Link URL | Context | Category (`auto-replace` / `requires-rewrite`) | Notes |
|---|---|---|---|---|
| .github/ISSUE_TEMPLATE/* | `https://github.com/open-webui/open-webui/issues` | Links to issues | `auto-replace` | Change to new repo URL |
| .github/ISSUE_TEMPLATE/* | `https://github.com/open-webui/open-webui/discussions` | Links to discussions | `auto-replace` | Change to new repo URL |
| .github/pull_request_template.md | `https://github.com/open-webui/docs` | Link to docs repo | `auto-replace` | Change to new docs repo URL |
| .github/workflows/deploy-to-hf-spaces.yml | `https://open-webui:${HF_TOKEN}@huggingface.co/spaces/open-webui/open-webui` | Git push URL | `auto-replace` | Change to new HF space |
| backend/open_webui/main.py | `https://docs.openwebui.com/license/` | License URL in API docs | `requires-rewrite` | Point to new license doc URL |
| backend/open_webui/main.py | `https://api.github.com/repos/open-webui/open-webui/releases/latest` | GitHub API for releases | `auto-replace` | Change to new repo URL |
| backend/open_webui/config.py | `https://api.openwebui.com/...` | API calls to external service | `requires-rewrite` | Review these API dependencies |
| backend/open_webui/env.py | `https://openwebui.com/favicon.png` | Favicon URL | `requires-rewrite` | Point to new asset path |
| backend/open_webui/routers/openai.py | `https://openwebui.com/` | HTTP Referer | `requires-rewrite` | Update referer if necessary |
| CHANGELOG.md | Multiple `https://github.com/open-webui/...` links | Links to various GitHub repos | `auto-replace` | Update to new repo/org URLs |
| CHANGELOG.md | Multiple `https://docs.openwebui.com/...` links | Links to documentation | `requires-rewrite` | Update to new documentation URLs |
| CODE_OF_CONDUCT.md | `hello@openwebui.com` | Reporting email | `requires-rewrite` | Change email address |
| README.md | Multiple `https://github.com/open-webui/...` links | Links to GitHub repos, star history, shields.io | `auto-replace` or `requires-rewrite` | Update to new repo/org URLs, badges may need new source |
| README.md | Multiple `https://docs.openwebui.com/...` links | Links to documentation | `requires-rewrite` | Update to new documentation URLs |
| README.md | `mailto:sales@openwebui.com` | Sales email | `requires-rewrite` | Change email address |
| README.md | `https://openwebui.com/` | Link to community site | `requires-rewrite` | Update to new community/project site URL |
| src/lib/components/*/*.svelte | Multiple `https://github.com/open-webui/...` links | Links to GitHub | `auto-replace` | Update to new repo/org URLs |
| src/lib/components/*/*.svelte | Multiple `https://docs.openwebui.com/...` links | Links to documentation | `requires-rewrite` | Update to new documentation URLs |
| src/lib/components/*/*.svelte | Multiple `https://openwebui.com/...` links | Links to community/main site | `requires-rewrite` | Update to new community/project site URLs |
| src/lib/constants.ts | `https://openwebui.com` (as WEBUI_BASE_URL default) | Default base URL | `requires-rewrite` | Update to new project URL or make it neutral |
| ... many more from grep results ... | | | |
---
*Notes on population:*
*   The "Textual References" table is populated by findings from `grep` for "Open WebUI", "OpenWebUI", and "open-webui". Due to the large number of results, only a representative sample is included above. The actual process would include all unique items.
*   CHANGELOG.md entries are included but should be reviewed carefully; historical mentions might be acceptable to keep as-is, or may need rephrasing if they imply current branding. For this map, they are listed.
*   i18n `translation.json` files contain many instances and are generally `auto-replace`.
*   `CONTRIBUTOR_LICENSE_AGREEMENT` content is `requires-rewrite`.
*   "Image & Asset References" are populated from `ls` results and `README.md` content.
*   "CSS Variables & Component Names" are based on common patterns and specific findings like `OTEL_SERVICE_NAME`. A deeper code review might find more.
*   "URLs & Links" are extracted from `grep` results, focusing on full URLs. GitHub links are generally `auto-replace` (to the new repo path), while `docs.openwebui.com` and `openwebui.com` links are `requires-rewrite`.
*   The term "TechSecAI Hub" appears in `README.md` and seems to be a new branding being introduced. This map focuses on "Open WebUI" removal, but the presence of "TechSecAI Hub" is noted as it will influence the replacement strategy. For this exercise, "Open WebUI" is the target for mapping.
*   The categorization (`auto-replace` vs `requires-rewrite`) is an initial assessment. `auto-replace` means a simple find/replace or file swap is likely sufficient. `requires-rewrite` indicates more complex changes, context-aware updates, or decisions (e.g., how to handle links to the old documentation site, or what to do with API dependencies).
---
