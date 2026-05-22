# ARCHGPU Bridge Integration (Custom Open WebUI Fork)

This document describes the customizations added on top of Open WebUI to
integrate ARCHGPU bridge model management directly inside the existing WebUI.

## What Is Customized

The following custom behavior is added:

- **No separate UI page** for catalogue management
- Model selector now includes:
  - installed models (normal behavior)
  - downloadable models (catalogue-backed)
  - in-place download action
  - live download progress display
- Quick delete action for installed bridge/Ollama models
- Admin `Model Explorer` tab for:
  - runtime live discovery of compatible models
  - metadata (freshness/downloads/likes/publisher/pipeline)
  - quality filters (trusted publishers + thresholds)
  - runtime fit recommendations (download guidance)

## Files Changed

- `backend/open_webui/routers/ollama.py`
  - Adds pass-through endpoints:
    - `GET /ollama/api/catalogue`
    - `GET /ollama/api/pull/status`
- `src/lib/apis/ollama/index.ts`
  - Adds frontend API helper for catalogue data.
- `src/lib/components/chat/ModelSelector/Selector.svelte`
  - Adds downloadable model section and pull trigger in selector dropdown.
- `src/lib/components/chat/ModelSelector/ModelItem.svelte`
  - Adds quick delete button in model list row.
- `src/lib/components/admin/Settings/ModelExplorer.svelte`
  - Adds full admin explorer for metadata/filter/recommendation workflows.
- `src/lib/components/admin/Settings.svelte`
  - Adds Model Explorer tab and routing.

## Build and Run (Custom Image)

```bash
cd /path/to/open-webui-src
docker build -t openwebui:archgpu-catalogue .
```

Run with your existing bridge stack helper:

```bash
cd /path/to/ARCHGPU_OLLAMA_BRIDGE
RECREATE_OPENWEBUI=1 OPENWEBUI_IMAGE=openwebui:archgpu-catalogue ./scripts/stack.sh up
```

## Usage

1. Open WebUI (`http://127.0.0.1:3000`).
2. Log in as admin.
3. Open model selector from chat input.
4. Download models directly from the **Downloadable** section.
5. Monitor download progress in the same selector UI.

## Compatibility Disclaimer

This custom fork is tested in a local environment on Ubuntu 26.04 with:

- Intel Arc GPU host setup
- Dockerized Open WebUI
- ARCHGPU bridge service exposing Ollama-compatible endpoints

Behavior on other operating systems, kernels, or Docker/network setups is not guaranteed.
Validate in your own environment before production usage.

## Publish This Fork To Your GitHub

```bash
cd /path/to/open-webui-src
git checkout -b archgpu-bridge-integration
git add backend/open_webui/routers/ollama.py src/lib/apis/ollama/index.ts src/lib/components/chat/ModelSelector/Selector.svelte src/lib/components/chat/ModelSelector/ModelItem.svelte src/lib/components/admin/Settings/ModelExplorer.svelte src/lib/components/admin/Settings.svelte README.md ARCHGPU_BRIDGE_INTEGRATION.md
git commit -m "Add native WebUI model explorer and bridge integration"

# set your own fork repo URL if needed
git remote set-url origin https://github.com/<your-user>/<your-openwebui-fork>.git
git push -u origin archgpu-bridge-integration
```
