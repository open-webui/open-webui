# GitLab Integration Plan

## Overview

Connect Open WebUI to GitLab to fetch repository contents, embed them into a vector store, and expose this data as knowledge for chat.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Docker Compose                                  │
│                                                                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌────────────┐ │
│  │   Backend   │   │   RAG       │   │  Vector DB  │   │  GitLab    │ │
│  │   (API)     │◄──│  Pipeline   │◄──│  (Chroma/   │   │  Worker    │ │
│  │             │   │             │   │  PGVector)  │   │            │ │
│  └─────────────┘   └──────┬──────┘   └─────────────┘   └─────┬──────┘ │
│        ▲                  │                                 │        │
│        │                  ▼                                 │        │
│        │           ┌─────────────┐                          │        │
│        │           │   Ollama    │                          │        │
│        │           │ (Embedding) │                          │        │
│        │           └─────────────┘                          │        │
│        │                                                      │        │
│        └──────────────┬──────────────────────────────────────┘        │
│                       │                                               │
│                       ▼                                               │
│               ┌─────────────────────┐                                  │
│               │       WebUI        │                                  │
│               │    (Frontend)      │                                  │
│               └─────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────────────┐
                    │         GitLab Instance               │
                    │  (SaaS or Self-hosted)                │
                    └───────────────────────────────────────┘
```

### Component Responsibilities

| Service | Role |
|---------|------|
| **Backend (Web API)** | Admin UI, config management, triggers sync jobs |
| **RAG Pipeline** | Text chunking, orchestration |
| **Ollama** | Embedding generation for text chunks (nomic-embed-text, etc.) |
| **Vector DB** | Stores embedded chunks (ChromaDB, PGVector, etc.) |
| **GitLab Worker** | Fetches repo content, coordinates ingestion |
| **Redis** | Job queue for async processing |

## GitLab Worker Service

A dedicated Docker Compose service handles the heavy lifting of connecting to GitLab, fetching repository contents, and coordinating with existing services for embedding.

### Service Definition

```yaml
services:
  gitlab-worker:
    build:
      context: .
      dockerfile: Dockerfile.gitlab-worker
    container_name: open-webui-gitlab-worker
    restart: unless-stopped
    volumes:
      - gitlab-worker-data:/app/data
    environment:
      - GITLAB_WORKER_ENABLED=true
      - GITLAB_WORKER_LOG_LEVEL=INFO
      - REDIS_URL=redis://redis:6379/0
      - RAG_PIPELINE_URL=http://backend:8080
      - VECTOR_DB_PROVIDER=${VECTOR_DB_PROVIDER}
      - VECTOR_DB_URL=${VECTOR_DB_URL}
    depends_on:
      - backend
      - redis
    networks:
      - open-webui-network
```

### Worker Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                         GitLab Worker                                  │
│                                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│  │  Job Queue   │───►│  GitLab      │───►│   Chunking   │            │
│  │  (Redis)     │    │  Fetcher     │    │   Service    │            │
│  └──────────────┘    └──────────────┘    └──────┬───────┘            │
│                                                  │                    │
│                                                  ▼                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│  │   Vector DB  │◄───│   Ollama     │◄───│   Embed      │            │
│  │   Storage    │    │   (Embed)    │    │   Request    │            │
│  └──────────────┘    └──────────────┘    └──────────────┘            │
└───────────────────────────────────────────────────────────────────────┘
```

### Worker Tasks

1. **Sync Job Processing**
   - Pick up sync jobs from Redis queue
   - Process repos sequentially or in parallel (configurable)
   - Track progress and report status

2. **Repository Fetching**
   - Clone/fetch repo via GitLab REST API
   - Recursive tree traversal for all files
   - Content retrieval with proper encoding
   - File filtering (include/exclude patterns)

3. **Chunking**
   - Split content into meaningful chunks
   - Respect code structures (functions, classes, files)
   - Apply configured chunk size limits

4. **Embedding via Ollama**
   - Send chunks to Ollama embedding endpoint (`/api/embeddings`)
   - Use configured embedding model (e.g., `nomic-embed-text`)
   - Collect returned embedding vectors

5. **Vector Storage**
   - Store embedded vectors in configured Vector DB
   - Associate with knowledge collection ID
   - Include metadata (file path, repo, branch)

6. **Status Updates**
   - Write progress to Redis (for WebSocket push to UI)
   - Store final status in backend database
   - Handle errors and retries

## Implementation Order

### Phase 1: Backend Service
1. Create `services/gitlab.py` - GitLab API client
   - Authentication with personal access token
   - Repository listing
   - File tree traversal
   - File content fetching

### Phase 2: Backend API
2. Modify `routers/configs.py` - Add GitLab config CRUD endpoints
3. Add config storage as `GITLAB_CONNECTIONS` (similar to `TOOL_SERVER_CONNECTIONS`)
4. Add Redis queue integration for job dispatch

### Phase 3: GitLab Worker Service
5. Create `Dockerfile.gitlab-worker` - Standalone worker image
6. Create `gitlab_worker/main.py` - Worker entrypoint
7. Create `gitlab_worker/job_queue.py` - Redis job handling
8. Create `gitlab_worker/gitlab_fetcher.py` - Repo content fetching
9. Create `gitlab_worker/chunker.py` - Text chunking logic
10. Create `gitlab_worker/embedder.py` - Ollama embedding integration
11. Create `gitlab_worker/vector_store.py` - Vector DB storage

### Phase 4: Ollama Integration (in Worker)
12. Implement Ollama client for embeddings
    - Connect to `OLLAMA_BASE_URL`
    - Use `OLLAMA_EMBEDDING_MODEL` for vector generation
    - Handle batching for large repos

### Phase 5: Frontend - Connection Management
13. Create `AddGitLabModal.svelte` - Connection form modal
14. Modify `Integrations.svelte` - Add GitLab section to admin tab
15. Add API methods to `apis/configs.ts`

### Phase 6: Knowledge UI
16. Knowledge page - Show GitLab repos as knowledge sources
    - View synced content
    - Trigger refresh/sync
    - Delete/unlink repos

### Phase 7: Integration with Chat
17. Works via existing `meta.knowledge` system
    - GitLab content stored as collections
    - Attached to models in ModelEditor
    - Chat middleware queries collection at runtime

## File Changes Summary

```
backend/
├── open_webui/
│   ├── services/
│   │   └── gitlab.py              # [NEW] GitLab API client (backend-side)
│   ├── routers/
│   │   └── configs.py             # [MOD] Add GitLab endpoints
│   └── models/
│       └── knowledge.py           # [MOD] Add GitLab type

gitlab-worker/                     # [NEW] Separate worker service
├── Dockerfile.gitlab-worker       # [NEW] Worker container image
├── requirements.txt               # [NEW] Worker dependencies
├── main.py                        # [NEW] Worker entrypoint
├── job_queue.py                   # [NEW] Redis job handling
├── gitlab_fetcher.py              # [NEW] Repo content fetching
├── chunker.py                     # [NEW] Text chunking logic
├── embedder.py                    # [NEW] Ollama embedding client
├── vector_store.py                # [NEW] Vector DB storage
└── config.py                      # [NEW] Worker configuration

src/
├── lib/
│   ├── components/
│   │   ├── admin/Settings/
│   │   │   └── Integrations.svelte  # [MOD] Add GitLab section
│   │   └── AddGitLabModal.svelte    # [NEW] GitLab config modal
│   └── apis/
│       └── configs.ts               # [MOD] Add GitLab API calls

docker-compose.yml                 # [MOD] Add gitlab-worker service
Dockerfile                         # [MOD] Reference for build context
```

## Docker Compose Integration

```yaml
# docker-compose.yml - Add to existing compose

services:
  # ... existing services (backend, webui, redis, vector db, ollama) ...

  gitlab-worker:
    build:
      context: .
      dockerfile: Dockerfile.gitlab-worker
    container_name: open-webui-gitlab-worker
    restart: unless-stopped
    volumes:
      - gitlab-worker-data:/app/data
    environment:
      - GITLAB_WORKER_ENABLED=true
      - GITLAB_WORKER_LOG_LEVEL=INFO
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_EMBEDDING_MODEL=${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}
      - VECTOR_DB_PROVIDER=${VECTOR_DB_PROVIDER:-chroma}
      - VECTOR_DB_URL=${VECTOR_DB_URL:-http://chroma:8000}
      - DATABASE_URL=${DATABASE_URL:-sqlite:///./open-webui.db}
    depends_on:
      - redis
      - ollama
      - chroma  # or pgvector, qdrant, etc.
    networks:
      - open-webui-network

volumes:
  gitlab-worker-data:

networks:
  open-webui-network:
    driver: bridge
```

## Worker Communication Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Backend API Container                             │
│                                                                          │
│  POST /api/v1/configs/gitlab/{id}/sync                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │ Save sync job   │───►│ Enqueue job to  │───►│  Return job ID  │      │
│  │ to database      │    │ Redis           │    │  to frontend    │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        GitLab Worker Container                           │
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │ Poll Redis      │───►│ Fetch repo via  │───►│ Chunk content   │      │
│  │ for jobs        │    │ GitLab API      │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘      │
│                                                           │               │
│                                                           ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Ollama (Embedding)                               │  │
│  │                                                                      │  │
│  │  POST /api/embeddings                                               │  │
│  │  Model: nomic-embed-text                                            │  │
│  │  Returns: embedding vectors                                          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                  │                                        │
│                                  ▼                                        │
│                       ┌──────────────────┐                               │
│                       │   Vector DB      │                               │
│                       │   (Chroma/PG)    │                               │
│                       └──────────────────┘                               │
└──────────────────────────────────────────────────────────────────────────┘
```

## Configuration Storage

GitLab connections stored as JSON array in config:
```json
{
  "GITLAB_CONNECTIONS": [
    {
      "id": "uuid",
      "name": "Company GitLab",
      "url": "https://gitlab.example.com",
      "token": "encrypted-token",
      "enabled": true,
      "auto_sync": false,
      "created_at": "ISO8601"
    }
  ]
}
```

## Token Security

- Personal Access Token stored encrypted via backend
- Same security pattern as tool server connections
- Token never exposed to frontend after initial save

## Supported GitLab Variants

- gitlab.com (SaaS)
- Self-hosted GitLab instances
- GitLab Enterprise

## Worker Dependencies

```txt
# gitlab-worker/requirements.txt

redis>=5.0.0
httpx>=0.25.0
python-gitlab>=4.0.0
pydantic>=2.0.0
structlog>=24.0.0
```

The worker relies on:
- **Redis**: Job queue (brpop/blpop for jobs)
- **Ollama**: Embedding endpoint (`/api/embeddings`) for vector generation
- **Vector DB**: Direct connection for storing embedded vectors
- **Database**: Sync status tracking via Backend API
- **GitLab API**: Repository content fetching

## Ollama Embedding Configuration

The worker uses Ollama for generating embeddings. Required environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |

Supported embedding models:
- `nomic-embed-text` (recommended, 768 dimensions)
- `mxbai-embed-large` (1536 dimensions)
- `paraphrase-multilingual` (768 dimensions)

## Future Enhancements (Out of Scope)

- Webhook-based auto-sync
- Commit/PR/issue integration
- Branch selection UI
- Selective folder/file sync