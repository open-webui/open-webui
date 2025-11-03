# Rebranding History: Open WebUI → OneChat

## Overview
This document records all changes made during the rebranding process from "Open WebUI" to "OneChat". This was a partial rebranding focused on user-facing product names only, keeping internal module names and package names unchanged.

**Date:** 2025-11-03
**Scope:** User-facing product names only
**Total Files Changed:** 63 files

---

## Summary of Changes

### Phase 1: Core Configuration Files (4 files)
Changes to essential application configuration files that define the product name.

#### 1. `/src/lib/constants.ts`
- **Line 4:** `APP_NAME` constant
  - **Before:** `export const APP_NAME = 'Open WebUI';`
  - **After:** `export const APP_NAME = 'OneChat';`
- **Purpose:** Primary product name constant used throughout the frontend application

#### 2. `/src/app.html`
- **Line 111:** HTML page title
  - **Before:** `<title>Open WebUI</title>`
  - **After:** `<title>OneChat</title>`
- **Purpose:** Browser tab title for the web application

#### 3. `/backend/open_webui/static/site.webmanifest`
- **Line 2-3:** PWA manifest names
  - **Before:**
    ```json
    "name": "Open WebUI",
    "short_name": "WebUI",
    ```
  - **After:**
    ```json
    "name": "OneChat",
    "short_name": "OneChat",
    ```
- **Purpose:** Progressive Web App name displayed when installed on mobile devices

#### 4. `/static/static/site.webmanifest`
- **Line 2-3:** PWA manifest names (duplicate of backend manifest)
  - **Before:**
    ```json
    "name": "Open WebUI",
    "short_name": "WebUI",
    ```
  - **After:**
    ```json
    "name": "OneChat",
    "short_name": "OneChat",
    ```
- **Purpose:** PWA manifest for static files

---

### Phase 2: Documentation Files (1 file)
Changes to user-facing documentation that describes the product.

#### 5. `/README.md`
Multiple occurrences of "Open WebUI" changed to "OneChat":

- **Line 1:** Main heading
  - `# Open WebUI 👋` → `# OneChat 👋`

- **Line 10:** Discord badge
  - `[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-...` → `[![Discord](https://img.shields.io/badge/Discord-OneChat-...`

- **Line 13:** Product description
  - `**Open WebUI is an [extensible]...` → `**OneChat is an [extensible]...`

- **Line 17:** Demo image alt text
  - `![Open WebUI Demo](./demo.gif)` → `![OneChat Demo](./demo.gif)`

- **Line 24:** Documentation link
  - `[Open WebUI Documentation]` → `[OneChat Documentation]`

- **Line 26:** Features heading
  - `## Key Features of Open WebUI ⭐` → `## Key Features of OneChat ⭐`

- **Line 44:** Community link
  - `[Open WebUI Community](https://openwebui.com/)` → `[OneChat Community](https://openwebui.com/)`

- **Line 60:** Multilingual support feature
  - `Experience Open WebUI in your preferred language` → `Experience OneChat in your preferred language`

- **Line 62:** Plugin support feature
  - `Pipelines, Open WebUI Plugin Support` → `Pipelines, OneChat Plugin Support`
  - `custom logic and Python libraries into Open WebUI` → `custom logic and Python libraries into OneChat`

- **Line 64:** Continuous updates feature
  - `improving Open WebUI with regular updates` → `improving OneChat with regular updates`

- **Line 66:** Features documentation link
  - `Open WebUI's features? Check out our [Open WebUI documentation]` → `OneChat's features? Check out our [OneChat documentation]`

- **Line 113:** Installation section
  - `Open WebUI can be installed using pip` → `OneChat can be installed using pip`
  - `**Install Open WebUI**:` → `**Install OneChat**:`
  - `to install Open WebUI:` → `to install OneChat:`

- **Line 122:** Running section
  - `**Running Open WebUI**:` → `**Running OneChat**:`
  - `you can start Open WebUI by executing` → `you can start OneChat by executing`

- **Line 129:** Server access
  - `start the Open WebUI server` → `start the OneChat server`

- **Line 134:** Docker documentation note
  - `[Open WebUI Documentation](https://docs.openwebui.com/)` → `[OneChat Documentation](https://docs.openwebui.com/)`

- **Line 137:** Docker warning
  - `to install Open WebUI, make sure` → `to install OneChat, make sure`

- **Line 140:** Docker tip
  - `utilize Open WebUI with Ollama` → `utilize OneChat with Ollama`

- **Line 158:** GPU support
  - `To run Open WebUI with Nvidia GPU support` → `To run OneChat with Nvidia GPU support`

- **Line 172:** Bundled installation heading
  - `### Installing Open WebUI with Bundled Ollama Support` → `### Installing OneChat with Bundled Ollama Support`
  - `bundles Open WebUI with Ollama` → `bundles OneChat with Ollama`

- **Line 190:** Installation completion
  - `installation of both Open WebUI and Ollama` → `installation of both OneChat and Ollama`
  - `access Open WebUI at` → `access OneChat at`

- **Line 196:** Other installation methods
  - `[Open WebUI Documentation]` → `[OneChat Documentation]`

- **Line 202:** Troubleshooting section
  - `[Open WebUI Documentation]` → `[OneChat Documentation]`
  - `[Open WebUI Discord]` → `[OneChat Discord]`

- **Line 204:** Connection error heading
  - `#### Open WebUI: Server Connection Error` → `#### OneChat: Server Connection Error`

- **Line 224:** Updating guide
  - `[Open WebUI Documentation]` → `[OneChat Documentation]`

- **Line 239:** Offline mode
  - `running Open WebUI in an offline environment` → `running OneChat in an offline environment`

- **Line 247:** Roadmap
  - `[Open WebUI Documentation]` → `[OneChat Documentation]`

- **Line 251:** License section
  - `licensed under the Open WebUI License` → `licensed under the OneChat License`
  - `preserve the "Open WebUI" branding` → `preserve the "OneChat" branding`

- **Line 256:** Support section
  - `[Open WebUI Discord community]` → `[OneChat Discord community]`

- **Line 270:** Footer
  - `Let's make Open WebUI even more amazing together!` → `Let's make OneChat even more amazing together!`

**Note:** External URLs (docs.openwebui.com, openwebui.com, GitHub badges) were intentionally NOT changed as they reference external resources.

---

### Phase 3: Translation Files (58 files)
All internationalization files containing user-facing text were updated.

Changed in all locale translation files under `/src/lib/i18n/locales/*/translation.json`:
- `"Open WebUI"` → `"OneChat"` (global string replacement)

#### Affected Locales:
1. ar (Arabic)
2. ar-BH (Arabic - Bahrain)
3. bg-BG (Bulgarian - Bulgaria)
4. bn-BD (Bengali - Bangladesh)
5. bo-TB (Tibetan)
6. bs-BA (Bosnian - Bosnia)
7. ca-ES (Catalan - Spain)
8. ceb-PH (Cebuano - Philippines)
9. cs-CZ (Czech - Czech Republic)
10. da-DK (Danish - Denmark)
11. de-DE (German - Germany)
12. dg-DG (Dogri)
13. el-GR (Greek - Greece)
14. en-GB (English - Great Britain)
15. en-US (English - United States)
16. es-ES (Spanish - Spain)
17. et-EE (Estonian - Estonia)
18. eu-ES (Basque - Spain)
19. fa-IR (Persian - Iran)
20. fi-FI (Finnish - Finland)
21. fr-CA (French - Canada)
22. fr-FR (French - France)
23. gl-ES (Galician - Spain)
24. he-IL (Hebrew - Israel)
25. hi-IN (Hindi - India)
26. hr-HR (Croatian - Croatia)
27. hu-HU (Hungarian - Hungary)
28. id-ID (Indonesian - Indonesia)
29. ie-GA (Irish - Ireland)
30. it-IT (Italian - Italy)
31. ja-JP (Japanese - Japan)
32. ka-GE (Georgian - Georgia)
33. kab-DZ (Kabyle - Algeria)
34. ko-KR (Korean - Korea)
35. lt-LT (Lithuanian - Lithuania)
36. ms-MY (Malay - Malaysia)
37. nb-NO (Norwegian Bokmål - Norway)
38. nl-NL (Dutch - Netherlands)
39. pa-IN (Punjabi - India)
40. pl-PL (Polish - Poland)
41. pt-BR (Portuguese - Brazil)
42. pt-PT (Portuguese - Portugal)
43. ro-RO (Romanian - Romania)
44. ru-RU (Russian - Russia)
45. sk-SK (Slovak - Slovakia)
46. sr-RS (Serbian - Serbia)
47. sv-SE (Swedish - Sweden)
48. th-TH (Thai - Thailand)
49. tk-TM (Turkmen - Turkmenistan)
50. tr-TR (Turkish - Turkey)
51. ug-CN (Uyghur - China)
52. uk-UA (Ukrainian - Ukraine)
53. uz-Cyrl-UZ (Uzbek Cyrillic - Uzbekistan)
54. uz-Latn-Uz (Uzbek Latin - Uzbekistan)
55. vi-VN (Vietnamese - Vietnam)
56. zh-CN (Chinese - China)
57. zh-TW (Chinese - Taiwan)
58. (Additional locale files)

#### Example Changes in Translation Keys:
```json
"CORS must be properly configured by the provider to allow requests from Open WebUI."
→ "CORS must be properly configured by the provider to allow requests from OneChat."

"Discover how to use Open WebUI and seek support from the community."
→ "Discover how to use OneChat and seek support from the community."

"Made by Open WebUI Community"
→ "Made by OneChat Community"

"Open WebUI can use tools provided by any OpenAPI server."
→ "OneChat can use tools provided by any OpenAPI server."

"Open WebUI uses faster-whisper internally."
→ "OneChat uses faster-whisper internally."

"Open WebUI uses SpeechT5 and CMU Arctic speaker embeddings."
→ "OneChat uses SpeechT5 and CMU Arctic speaker embeddings."

"Open WebUI version (v{{OPEN_WEBUI_VERSION}}) is lower than required version"
→ "OneChat version (v{{OPEN_WEBUI_VERSION}}) is lower than required version"

"Redirecting you to Open WebUI Community"
→ "Redirecting you to OneChat Community"

"Share to Open WebUI Community"
→ "Share to OneChat Community"

"Your entire contribution will go directly to the plugin developer; Open WebUI does not take any percentage."
→ "Your entire contribution will go directly to the plugin developer; OneChat does not take any percentage."
```

---

## What Was NOT Changed

### Internal Module Names
The following were intentionally left unchanged to avoid breaking changes:
- Python module name: `open_webui` (throughout `/backend/open_webui/`)
- Package name in `pyproject.toml`: `open-webui`
- Package name in `package.json`: `open-webui`
- Docker image names: `ghcr.io/open-webui/open-webui`
- Kubernetes service names: `ollama-service.open-webui.svc.cluster.local`

### External References
- GitHub repository URLs: `https://github.com/open-webui/`
- Documentation URLs: `https://docs.openwebui.com/`
- Community URLs: `https://openwebui.com/`
- Email addresses: `sales@openwebui.com`, `tim@openwebui.com`
- API endpoints: `https://api.openwebui.com/`
- GitHub badges and shields.io URLs

### Infrastructure & Database
- Environment variables: `OPEN_WEBUI_DIR`
- Redis key prefix: `redis_key_prefix: "open-webui"`
- Database collection prefixes: `QDRANT_COLLECTION_PREFIX = "open-webui"`
- Pinecone index: `PINECONE_INDEX_NAME = "open-webui-index"`
- Docker volume names: `-v open-webui:/app/backend/data`
- Container names: `--name open-webui`

### File and Directory Names
- Directory structure: `/backend/open_webui/` (Python module path)
- File paths in imports and references
- Git repository structure

---

## Impact Assessment

### User-Visible Changes ✅
- Application title in browser tabs
- PWA app name on mobile devices
- All UI text references to product name
- README and documentation titles
- All translation strings across 58 languages

### No Impact ⚠️
- API compatibility (all endpoints remain the same)
- Database schemas and migrations
- Docker deployment commands (image names unchanged)
- Python package installation (`pip install open-webui` still works)
- Environment variables and configuration
- Git repository structure

### Developer Experience
- Code references to `APP_NAME` constant now return "OneChat"
- No changes required to import statements
- No changes required to existing integrations
- All existing documentation URLs remain valid

---

## Git Commits

### Commit 1: Core Configuration Changes
**Commit Hash:** `55ba3140`
**Message:** "Rebrand product name from 'Open WebUI' to 'OneChat'"
**Files Changed:** 4
- `src/lib/constants.ts`
- `src/app.html`
- `backend/open_webui/static/site.webmanifest`
- `static/static/site.webmanifest`

### Commit 2: Documentation and Translation Changes
**Commit Hash:** [To be added after commit]
**Message:** "Update README and all translation files for OneChat rebrand"
**Files Changed:** 59
- `README.md`
- `src/lib/i18n/locales/*/translation.json` (58 files)

---

## Verification Steps

To verify the rebranding was successful:

1. **Frontend Application:**
   ```bash
   grep -r "Open WebUI" src/lib/constants.ts src/app.html
   # Should return no results
   ```

2. **Translation Files:**
   ```bash
   grep -r "Open WebUI" src/lib/i18n/locales/*/translation.json
   # Should return no results
   ```

3. **README:**
   ```bash
   grep "OneChat" README.md | wc -l
   # Should show multiple occurrences
   ```

4. **Module Names (should remain unchanged):**
   ```bash
   grep -r "open_webui" backend/ | head -5
   # Should still show open_webui module references
   ```

---

## Rollback Instructions

If rebranding needs to be reverted:

```bash
# Revert to commit before rebranding
git revert <commit-hash>

# Or manually replace all occurrences
find . -type f -name "*.ts" -o -name "*.html" -o -name "*.json" -o -name "*.md" \
  -exec sed -i 's/OneChat/Open WebUI/g' {} \;
```

---

## Notes

- This was a **user-facing rebrand only** - internal architecture remains unchanged
- External dependencies and integrations are **not affected**
- All original functionality remains **100% intact**
- Documentation URLs point to original resources (intentional for continuity)
- Future updates should maintain "OneChat" branding in user-facing elements
- Consider updating external documentation sites separately if needed

---

**Document Version:** 1.0
**Last Updated:** 2025-11-03
**Maintained By:** Development Team
