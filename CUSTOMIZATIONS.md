# Customizations: Modifications from Upstream Open WebUI

## 2025-07-15: Image Content Extraction
- Backend: Enabled images in default processing pipeline (commit 743e03645)
  - Removed image exclusion from `process_file()` logic
  - Images now processed through content extraction engine
- Frontend: Images upload to backend for content extraction alongside vision processing (commit 697691efe)
  - Update `MessageInput.svelte` to show progress indicator for image uploads (commit d32d8d38a)
- Result: Images get OCR text extracted for RAG

## 2025-07-15: Docker Build
- Custom GitHub Actions workflow
- Multi-platform: AMD64 + ARM64
- Builds to `ghcr.io/farzammohammadi/open-webui:main`