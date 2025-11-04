# Open WebUI Enterprise Mode

This document outlines the strategic vision, architecture, and operational profile for Enterprise Mode. It summarizes what changes versus the full (local) profile and how to extend the system with new SaaS providers using our service-oriented design.

## Strategic Vision
- Service-Oriented Architecture for all AI/ML/CV and Vector DB features.
- Local ML/CV runtimes are not required in Enterprise Mode; all heavy lifting is delegated to managed SaaS.
- Uniform service contracts and DI (dependency injection) make providers plug-and-play, with strict import boundaries to keep the footprint small and startup fast.

## What’s Different in Enterprise Mode
- No local ML/CV inference imports on startup (torch, sentence-transformers, faster-whisper, chromadb, rapidocr, colbert, onnxruntime).
- Only allowable local work: non-ML preprocessing (e.g., string ops, chunking, simple byte/audio file handling without ML libraries).
- Engines default to SaaS providers:
  - Embeddings: OpenAI (or Azure OpenAI)
  - Reranker: External HTTP provider
  - STT/TTS: OpenAI (or Azure)
  - OCR: Azure Document Intelligence (or AWS Textract)
  - Vector DB: pgvector

## Architecture Overview
- Contracts (service interfaces): `backend/open_webui/services/interfaces.py`
  - `EmbeddingService`, `RerankerService`, `STTService`, `TTSService`, `OCRService`, `VectorDBService`.
- Providers (adapters): `backend/open_webui/services/providers/*`
  - SaaS providers (OpenAI, Azure, Deepgram, Pinecone, Qdrant, PGVector, etc.).
  - Local providers exist only for the full profile; never imported in Enterprise Mode.
- Provider registry and DI: `backend/open_webui/services/registry.py`, `backend/open_webui/services/dependencies.py`
  - Resolves provider by selected engine; lazily imports optional SDKs only when needed.
- Settings: `backend/open_webui/settings.py`
  - Flags: `enterprise_mode`, `local_features_enabled` (false in Enterprise), engine selections, credential validation.
- Error Model
  - LocalFeatureDisabledError → 501 Not Implemented (local provider requested in Enterprise mode)
  - ProviderConfigurationError → 400 Bad Request (missing/invalid credentials)
  - UpstreamServiceError → 502 Bad Gateway (SaaS failure)

## Retrieval, Audio, OCR, Vector DB (Key Changes)
- Retrieval
  - Routers call the DI services; no direct model management in routes/utilities.
  - Hybrid search consumes `VectorDBService` results rather than Chroma-specific shapes.
  - Local model downloads reside only in local providers; enterprise import graph excludes Hugging Face/torch.
- Audio
  - STT/TTS routed via SaaS providers. Admin update paths gate local engines in Enterprise.
  - Non-ML pydub-based conversions are allowed and kept minimal.
- Documents/OCR
  - Driven by `OCRService` (e.g., Azure Document Intelligence or AWS Textract) rather than direct SDK usage in routers.
- Vector DB
  - Normalized to `VectorDBService` with adapters for pgvector, Pinecone, Qdrant, etc.
  - Optional SDKs (boto3, cloud clients) import lazily only if that provider is selected.

## Enterprise Profiles and Defaults
- Profiles:
  - `config/profiles/enterprise.yaml`: Enterprise defaults (SaaS engines, pgvector, local features disabled).
  - `config/profiles/full.yaml`: Full/local default profile for self-hosted ML.
- Enterprise default engines (can be overridden via env):
  - `RAG_EMBEDDING_ENGINE=openai`
  - `RAG_RERANKING_ENGINE=external`
  - `AUDIO_STT_ENGINE=openai`
  - `AUDIO_TTS_ENGINE=openai`
  - `VECTOR_DB=pgvector`
  - `OCR_ENGINE=azure_document_intelligence`

## Docker and Compose
- Dockerfile detects Enterprise Mode with `--build-arg USE_ENTERPRISE_MODE=true` and:
  - Installs only `backend/requirements-base.txt` + `backend/requirements-enterprise.txt`.
  - Omits apt packages used solely for local ML/CV (ffmpeg, libsm6, libxext6, pandoc).
  - Sets `ENTERPRISE_MODE=true` and `LOCAL_MODE_DISABLED=true` in the image.
- Compose (enterprise)
  - `docker-compose.enterprise.yaml` runs Open WebUI in enterprise mode with default SQLite (app DB) and Chroma (vector DB).
  - Optional overlay: `docker-compose.enterprise.data.yaml` bind-mounts host data.

## Quickstart / Launch

Option A — Compose (recommended)
```
# Use the provided defaults (or copy to .env)
docker compose --env-file .env.enterprise -f docker-compose.enterprise.yaml up -d --build

# Check health
curl localhost:${OPEN_WEBUI_PORT:-3000}/health

# Tail logs
docker compose -f docker-compose.enterprise.yaml logs -f open-webui-enterprise
```
Compose auto-loads a local `.env` file for `${VAR}` expansion, or use `--env-file .env.enterprise` to load the defaults we ship. Useful variables:
- `OPENAI_API_KEY=...`
- `RAG_EXTERNAL_RERANKER_URL=...`, `RAG_EXTERNAL_RERANKER_API_KEY=...`
- `DOCUMENT_INTELLIGENCE_ENDPOINT=...`, `DOCUMENT_INTELLIGENCE_KEY=...`
  (No database env is required by default; app uses SQLite and Chroma.)

Conditional installs (build-time)
- The enterprise Docker build installs only the selected vector DB client:
  - Set `VECTOR_DB` in `.env` or `ENTERPRISE_VECTOR_DB` build arg to one of: `chroma`, `pgvector`, `pinecone`, `qdrant`, `milvus`.
  - Defaults to `chroma`. The Dockerfile installs the matching `requirements-vectordb-*.txt` during the enterprise build.

Notes:
- The container and app start even if these variables are empty. When you invoke a feature without required credentials, the API returns a clear 400 error indicating the provider is not configured.
- A named volume is used by default; add `-f docker-compose.enterprise.data.yaml` to bind-mount local data if desired.

Option B — Direct Docker
```
docker build -t openwebui:enterprise \
  --build-arg USE_ENTERPRISE_MODE=true \
  --build-arg USE_SLIM=true \
  --build-arg BUILD_HASH=$(git rev-parse --short HEAD) .

docker run --rm -p 3000:8080 openwebui:enterprise

# Health
curl localhost:3000/health
```
Direct Docker runs without external databases by default (SQLite + Chroma). The app still starts; features that need provider credentials will return a configuration error until configured.

## Extensibility: Adding a New SaaS Provider
1) Implement provider under `backend/open_webui/services/providers/` with lazy imports and a thin `httpx` client.
2) Register it in `backend/open_webui/services/registry.py` under a distinct engine key; validate credentials in `Settings` when selected.
3) Expose it via DI (dependencies accessors) and raise `ProviderConfigurationError` when misconfigured.
4) Optional: add a minimal health check or rely on registry wiring for `/api/v1/system/health`.

## Performance & Robustness
- Batch requests where safe; bound retries with jitter for SaaS adapters.
- Use `asyncio.to_thread` for any CPU-bound local code-paths (full profile only).
- Surface upstream request IDs when available; never log secrets.

## Security & Compliance
- No secrets in logs; secrets come from environment settings.
- Enterprise Mode avoids bundling or importing local ML/CV runtimes by default, reducing attack surface and footprint.

## Backward Compatibility
- Route signatures and response shapes preserved.
- Full/local profile remains available; Enterprise defaults can be disabled by building without `USE_ENTERPRISE_MODE`.

---

This document summarizes the rationale and mechanics of Enterprise Mode to support our PR/issue narrative: A service-oriented, SaaS-first posture that eliminates the need to ship or operate heavyweight local ML/CV runtimes while keeping the codebase modular, pluggable, and backward compatible.
