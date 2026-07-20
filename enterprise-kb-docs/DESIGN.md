# Design Document: Enterprise Knowledge Base Management Dashboard

> A technical design document for the RAG observability and management layer added to Open WebUI.

**Author**: Guyang (yangyang-qaq)
**Date**: 2026-07-21
**Status**: Complete (All 6 phases implemented)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [System Architecture](#3-system-architecture)
4. [Database Design](#4-database-design)
5. [API Design](#5-api-design)
6. [Frontend Design](#6-frontend-design)
7. [Data Flow](#7-data-flow)
8. [Phase 6: Prompt Template Management](#8-phase-6-prompt-template-management)
9. [Trade-offs & Decisions](#9-trade-offs--decisions)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Problem Statement

### 1.1 Current State (Before)

Open WebUI's knowledge base feature has a **black-box problem**:

- Users upload documents but have **no visibility** into how they are chunked
- There is **no way to verify** chunk quality — a bad split silently degrades retrieval
- Document processing has **no progress feedback** — users don't know if it's working or stuck
- Retrieval quality is **unmeasurable** — no recall, precision, or relevance metrics
- Knowledge base state has **no versioning** — adding/removing files is irreversible
- RAG prompt templates are **global only** — no per-knowledge-base customization

### 1.2 Target Users

- **Knowledge base administrators** who need to curate and maintain KB quality
- **RAG developers** who need to evaluate and optimize retrieval pipelines
- **End users** who want to understand why certain documents are retrieved

---

## 2. Goals & Non-Goals

### Goals

| # | Goal | Success Metric |
|---|---|---|
| G1 | Visualize chunking results before vectorization | Users can preview chunks for any file |
| G2 | Allow manual chunk adjustment | Users can merge/split chunks and reindex |
| G3 | Real-time processing progress | Progress updates within 3 seconds of state change |
| G4 | Measure retrieval quality | Compute recall@K, precision@K, MRR from annotations |
| G5 | Version control for KB state | Create, rollback, compare snapshots |
| G6 | Per-KB prompt template configuration | Custom RAG prompts with variable substitution |

### Non-Goals

- Replacing ChromaDB with a different vector store
- Multi-user collaborative annotation workflows
- Automated chunk strategy optimization
- Real-time collaborative editing of prompts

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     SvelteKit Frontend                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │            Tab Navigation (+layout.svelte)            │ │
│  │  Files │ Chunks │ Processing │ Evaluate │ Snapshots  │ │
│  └─────────────────────────────────────────────────────┘ │
│                          │ HTTP + SSE                     │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                   FastAPI Backend                          │
│  ┌───────────────────────┴──────────────────────────────┐ │
│  │              Knowledge Router                         │ │
│  │  /api/v1/knowledge/{id}/                              │ │
│  │  ├── chunks/*        (7 endpoints)                    │ │
│  │  ├── progress/*      (3 endpoints)                    │ │
│  │  ├── evaluate/*      (4 endpoints)                    │ │
│  │  ├── snapshots/*     (5 endpoints)                    │ │
│  │  └── prompt          (2 endpoints)                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                            │                               │
│  ┌─────────────┬───────────┼───────────┬────────────────┐ │
│  │ SQLAlchemy  │ ChromaDB  │ In-Memory │ LLM API        │ │
│  │ ORM         │ Client    │ Store     │ Client         │ │
│  └──────┬──────┘ └────┬─────┘ └────┬────┘ └──────┬───────┘ │
└─────────┼─────────────┼────────────┼──────────────┼─────────┘
          │             │            │              │
   ┌──────┴──────┐ ┌───┴────┐ ┌────┴─────┐ ┌─────┴──────┐
   │ SQLite/PG   │ │ChromaDB│ │ _progress│ │DeepSeek API│
   │ (5 tables)  │ │(vectors)│ │ _store   │ │(inference) │
   └─────────────┘ └────────┘ └──────────┘ └────────────┘
```

### 3.2 Technology Choices

| Component | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI (existing) | Already used by Open WebUI; async support needed for SSE |
| ORM | SQLAlchemy (existing) | Alembic migrations, async session, SQLite/PG compatibility |
| Vector store | ChromaDB (existing) | Embedded, no external service; sufficient for KB scale |
| Realtime updates | SSE + Polling | SSE for low latency; 3s polling as fallback for reliability |
| Frontend | SvelteKit (existing) | Matches existing codebase; Tailwind CSS for styling |
| Evaluation metrics | Server-side Python | Keep computation close to data; avoid sending raw results to client |

---

## 4. Database Design

### 4.1 Entity-Relationship Diagram

```
knowledge ──< knowledge_file >── file
     │               │
     │               ├── knowledge_chunk
     │               │     (chunk_index, content, content_hash, token_count, meta)
     │               │
     │               ├── knowledge_processing_task
     │               │     (status, progress_pct, chunks_total, chunks_processed)
     │               │
     │               └── knowledge_batch_task
     │                     (total_files, files_processed, status)
     │
     ├── knowledge_relevance_judgment
     │     (query_text, document_id, relevant, rank, score)
     │
     └── knowledge_snapshot
           (snapshot_data JSON, file_count, chunk_count, label)
```

### 4.2 Table Schemas

#### `knowledge_chunk`
```sql
CREATE TABLE knowledge_chunk (
    id            TEXT PRIMARY KEY,           -- UUID
    knowledge_id  TEXT NOT NULL,              -- FK → knowledge.id
    file_id       TEXT NOT NULL,              -- FK → file.id
    chunk_index   BIGINT NOT NULL,            -- 0-based ordering
    content       TEXT NOT NULL,              -- Full chunk text
    token_count   BIGINT,                     -- Estimated token count
    meta          JSON,                       -- {page, section_header, ...}
    content_hash  TEXT,                       -- SHA-256 for dedup/diff
    created_at    BIGINT NOT NULL,
    updated_at    BIGINT NOT NULL,

    UNIQUE(file_id, chunk_index),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES file(id) ON DELETE CASCADE
);

CREATE INDEX ix_knowledge_chunk_knowledge_id ON knowledge_chunk(knowledge_id);
CREATE INDEX ix_knowledge_chunk_file_id ON knowledge_chunk(file_id);
```

**Design Rationale**:
- `content_hash` enables snapshot comparison without storing full text
- `UNIQUE(file_id, chunk_index)` prevents duplicate indices during reindexing
- `ON DELETE CASCADE` ensures cleanup when KB or file is removed

#### `knowledge_processing_task`
```sql
CREATE TABLE knowledge_processing_task (
    id              TEXT PRIMARY KEY,
    knowledge_id    TEXT NOT NULL,
    file_id         TEXT,
    task_type       TEXT NOT NULL,     -- 'chunking' | 'embedding' | 'full_process'
    status          TEXT NOT NULL,     -- 'pending'|'chunking'|'embedding'|'completed'|'failed'
    progress_pct    BIGINT NOT NULL DEFAULT 0,
    chunks_total    BIGINT,
    chunks_processed BIGINT,
    error_message   TEXT,
    created_at      BIGINT NOT NULL,
    updated_at      BIGINT NOT NULL,

    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES file(id) ON DELETE CASCADE
);
```

**Design Rationale**:
- Separate table (not in `meta` JSON) enables efficient querying and indexing
- `progress_pct` provides a simple percentage for UI progress bars
- `error_message` captures failure reasons for user feedback

#### `knowledge_relevance_judgment`
```sql
CREATE TABLE knowledge_relevance_judgment (
    id              TEXT PRIMARY KEY,
    knowledge_id    TEXT NOT NULL,
    query_text      TEXT NOT NULL,
    document_id     TEXT NOT NULL,
    relevant        BOOLEAN NOT NULL,
    rank            BIGINT,            -- Position in search results (0-based)
    score           FLOAT,             -- Similarity score from vector search
    created_at      BIGINT NOT NULL,

    UNIQUE(knowledge_id, query_text, document_id),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
);
```

**Design Rationale**:
- `UNIQUE(knowledge_id, query_text, document_id)` prevents duplicate annotations
- `rank` and `score` are stored at annotation time for consistent metrics

#### `knowledge_snapshot`
```sql
CREATE TABLE knowledge_snapshot (
    id              TEXT PRIMARY KEY,
    knowledge_id    TEXT NOT NULL,
    label           TEXT,              -- Human-readable label
    snapshot_data   JSON NOT NULL,     -- {files: [...], chunks: [...], created_at: ...}
    file_count      BIGINT,
    chunk_count     BIGINT,
    created_at      BIGINT NOT NULL,

    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE
);
```

**Design Rationale**:
- JSON snapshot data is self-contained — no dependency on current DB state
- File/chunk counts stored redundantly for list display without parsing JSON

---

## 5. API Design

### 5.1 Design Principles

1. **RESTful conventions**: Resources nested under `/knowledge/{id}/`
2. **Existing auth**: Reuse Open WebUI's JWT authentication and RBAC
3. **Consistent error handling**: Standard FastAPI error responses
4. **Backward compatibility**: No breaking changes to existing endpoints

### 5.2 Chunk Management APIs

#### POST `/{id}/chunks/preview` — Chunk Preview

Runs the loader + splitter pipeline without writing to ChromaDB. Results are persisted in `knowledge_chunk` for later retrieval.

**Flow**:
```
1. Look up file_id → get file path
2. Storage.get_file() → local file
3. build_loader_from_config() → document Loader (PDF/DOCX/...)
4. loader.aload() → extract text
5. MarkdownHeaderTextSplitter (optional) → structure-aware split
6. RecursiveCharacterTextSplitter / TokenTextSplitter → content-aware split
7. DELETE existing chunks for this file_id
8. INSERT new chunks into knowledge_chunk table
9. Return chunk list
```

#### POST `/{id}/chunks/merge` — Merge Chunks

```python
# Pseudocode
def merge_chunks(knowledge_id, file_id, start_index, end_index):
    # 1. Read chunks in [start_index, end_index]
    chunks = read_chunks_in_range(file_id, start_index, end_index)
    # 2. Concatenate content with \n\n
    merged_content = "\n\n".join(ch.content for ch in chunks)
    # 3. Insert merged chunk at start_index
    insert_chunk(file_id, start_index, merged_content)
    # 4. Delete original chunks
    delete_chunks_in_range(file_id, start_index, end_index)
    # 5. Renumber remaining chunks (shift by -(end_index - start_index))
    renumber_chunks(file_id, anchor=end_index + 1, offset=-(end_index - start_index))
```

**Constraint**: Only consecutive chunks (by `chunk_index`) can be merged.

#### POST `/{id}/chunks/split` — Split a Chunk

```python
def split_chunk(chunk_id, split_at):
    chunk = read_chunk(chunk_id)
    part_a = chunk.content[:split_at]
    part_b = chunk.content[split_at:]
    # Update original → part_a
    update_chunk(chunk_id, content=part_a)
    # Insert part_b at next index
    insert_chunk(file_id, chunk.chunk_index + 1, content=part_b)
    # Shift all subsequent chunks by +1
    shift_chunks(file_id, anchor=chunk.chunk_index + 1, offset=+1)
```

**Constraint**: `split_at` must be between 1 and `len(content)-1`, and both parts must be non-empty.

#### POST `/{id}/chunks/reindex` — Rebuild Vectors

```python
def reindex_chunks(knowledge_id):
    chunks = read_all_chunks(knowledge_id)
    delete_chromadb_collection(knowledge_id)
    documents = [chunk_to_langchain_doc(c) for c in chunks]
    save_docs_to_vector_db(documents)
```

### 5.3 Progress Tracking APIs

#### SSE Stream: `GET /{id}/progress/stream`

```python
async def stream_progress(knowledge_id):
    async def event_generator():
        while True:
            tasks = get_tasks(knowledge_id)
            yield f"data: {json.dumps(tasks)}\n\n"
            # Terminate when all tasks are terminal
            if all(t.status in ("completed", "failed") for t in tasks):
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Architecture**: Dual-write pattern — each progress update writes to both:
1. **DB** (`knowledge_processing_task` table) → persistence
2. **In-memory dict** (`_progress_store`) → fast SSE reads

```
_update_processing_progress(kb_id, file_id, status, pct):
    DB: upsert knowledge_processing_task
    Memory: _progress_store[kb_id][file_id] = {...}
```

### 5.4 Evaluation Metrics

Server-side computation from stored annotations:

```python
def compute_metrics(knowledge_id, query_text, k):
    judgments = get_judgments(knowledge_id, query_text)
    total_relevant = sum(1 for j in judgments if j.relevant)
    retrieved = judgments[:k]

    recall = sum(1 for r in retrieved if r.relevant) / total_relevant if total_relevant > 0 else 0
    precision = sum(1 for r in retrieved if r.relevant) / k
    mrr = max((1 / (j.rank + 1) for j in judgments if j.relevant), default=0)

    return {"recall@K": recall, "precision@K": precision, "mrr": mrr}
```

### 5.5 Snapshot APIs

#### POST `/{id}/snapshots` — Create Snapshot

```python
def create_snapshot(knowledge_id, label):
    files = get_kb_file_associations(knowledge_id)
    chunks = get_all_chunks(knowledge_id)
    snapshot_data = json.dumps({
        "files": [{"file_id": f.file_id} for f in files],
        "chunks": [{"id": c.id, "file_id": c.file_id, "chunk_index": c.chunk_index,
                     "content_hash": c.content_hash} for c in chunks],
        "created_at": now()
    })
    insert_snapshot(knowledge_id, label, snapshot_data, len(files), len(chunks))
```

#### POST `/{id}/snapshots/{sid}/rollback` — Rollback

```python
def rollback_snapshot(knowledge_id, snapshot_id):
    snapshot = get_snapshot(snapshot_id)
    data = json.loads(snapshot.snapshot_data)

    # 1. Clear current state
    delete_all_chunks(knowledge_id)
    delete_all_file_associations(knowledge_id)

    # 2. Restore from snapshot
    for file_ref in data["files"]:
        restore_file_association(knowledge_id, file_ref["file_id"])
    for chunk_ref in data["chunks"]:
        restore_chunk_metadata(knowledge_id, chunk_ref)

    # 3. Note: vectors must be reindexed manually via Chunks tab
    return {"restored_files": len(data["files"]), "restored_chunks": len(data["chunks"])}
```

**Key Trade-off**: Snapshots store file_id references, not file content. If a file is physically deleted (`delete_file=true`), rollback cannot restore it. This is why we added the **"Unlink Only"** button (`?delete_file=false`).

---

## 6. Frontend Design

### 6.1 Component Tree

```
knowledge/[id]/
├── +layout.svelte           ← Tab navigation bar (5 tabs)
├── +page.svelte             ← Files view (KnowledgeBase component)
├── chunks/
│   └── +page.svelte         ← ChunkManager component
├── processing/
│   └── +page.svelte         ← ProcessingDashboard component
├── evaluate/
│   └── +page.svelte         ← EvaluatePanel component
└── snapshots/
    └── +page.svelte         ← SnapshotManager component
```

### 6.2 Component Design

#### ChunkManager
```
┌───────────────────────────────────────────────┐
│ ← Back to KB    Chunk Manager    [Reindex]     │
├───────────────────────────────────────────────┤
│ File: [dropdown ▼]           125 chunks        │
├──────┬────────┬──────────────────┬────────────┤
│  #   │  ☑     │ Content Preview  │  Actions   │
├──────┼────────┼──────────────────┼────────────┤
│  0   │  ☐     │ Transformer...    │ View Split │
│  1   │  ☑     │ The evolution...  │ View Split │
│  2   │  ☑     │ RAG combines...   │ View Split │
└──────┴────────┴──────────────────┴────────────┘
         [Merge Selected (2)]
```

**States**: Empty (no file selected), Loading (fetching chunks), Loaded, No chunks yet (file not processed)

#### ProcessingDashboard
```
┌───────────────────────────────────────────────┐
│ Processing Status                    [Live ●]  │
├───────────────────────────────────────────────┤
│ Overall: 3/5 completed                         │
│ ██████████████░░░░░░░░ 60%                     │
├───────────────────────────────────────────────┤
│ file-abc...  [Embedding]             50%       │
│ ██████████░░░░░░░░░░  60/120 chunks            │
│                                                 │
│ file-def...  [Completed]             100%       │
│ ██████████████████████  80/80 chunks            │
│                                                 │
│ file-ghi...  [Failed]                 0%        │
│ ░░░░░░░░░░░░░░░░░░░░░░  ⚠ Connection timeout   │
└───────────────────────────────────────────────┘
```

**Data Flow**: SSE (primary) → instant update | Polling (fallback) → 3s interval

#### EvaluatePanel
```
┌───────────────────────────────────────────────┐
│ Retrieval Evaluation                           │
├───────────────────────────────────────────────┤
│ [Query input...]           [K=10 ▼] [Search]   │
├───────┬───────┬────────┬───────┐               │
│ 0.50  │ 0.40  │ 1.000  │   2   │               │
│Recall │Prec   │  MRR   │Relvnt │               │
├───────┴───────┴────────┴───────┘               │
│ #1 score:0.89  Transformer...    [✓] [✗]      │
│ #2 score:0.78  Large language...  [✓] [✗]      │
│ #3 score:0.65  RAG techniques...  [✓] [✗]      │
├───────────────────────────────────────────────┤
│ ▶ RAG Prompt Template  [Edit]                   │
│   [textarea with {query} {context} {kb_name}]   │
└───────────────────────────────────────────────┘
```

### 6.3 State Management

Each component manages its own state locally via Svelte stores. No global state management was added — components fetch data on mount and refetch on actions.

---

## 7. Data Flow

### 7.1 File Upload → Chunk → Progress Flow

```
User uploads file
    │
    ▼
POST /api/v1/knowledge/{id}/file/add
    │
    ├── 1. _update_processing_progress(status='chunking', progress=20)
    │       ├── DB: INSERT/UPDATE knowledge_processing_task
    │       └── Memory: _progress_store[kb_id][file_id] = {...}
    │
    ├── 2. process_file()
    │       ├── build_loader_from_config() → Loader
    │       ├── loader.aload() → Documents
    │       ├── MarkdownHeaderTextSplitter → structure split
    │       ├── RecursiveCharacterTextSplitter → content split
    │       └── save_docs_to_vector_db() → ChromaDB
    │
    ├── 3. Write chunks to knowledge_chunk table
    │       (extracted from ChromaDB results)
    │
    ├── 4. _update_processing_progress(status='completed', progress=100)
    │
    └── 5. Return to user
            │
            ▼
    SSE subscriber receives update → ProcessingDashboard re-renders
```

### 7.2 Snapshot → Rollback Flow

```
User creates snapshot
    │
    ▼
POST /snapshots
    ├── Collect all file_id from knowledge_file
    ├── Collect all chunk metadata from knowledge_chunk
    └── Store as JSON in knowledge_snapshot

User clicks Rollback
    │
    ▼
POST /snapshots/{sid}/rollback
    ├── 1. Delete all knowledge_chunk rows for this KB
    ├── 2. Delete all knowledge_file associations (unlink, not delete files)
    ├── 3. Restore file associations from snapshot data
    ├── 4. Restore chunk metadata from snapshot data
    └── 5. Return summary → user manually reindexes if needed
```

---

## 8. Phase 6: Prompt Template Management

### 8.1 Schema

Prompt templates are stored in the existing `knowledge.meta` JSON field (no new table needed):

```json
{
  "rag_prompt_template": "You are a knowledge base assistant. Answer based on the references below.\n\nReferences:\n{context}\n\nQuestion: {query}\n\nIf the references do not contain relevant information, say so honestly."
}
```

### 8.2 Chat Pipeline Integration

In `utils/middleware.py`, the `apply_source_context_to_messages()` function was extended:

```python
# Pseudocode for prompt injection
for source in sources:
    if source is a knowledge base:
        kb = get_knowledge(source.id)
        custom_template = kb.meta.get("rag_prompt_template")
        if custom_template:
            # Transform variables: {query}→[query], {context}→[context], {kb_name}→kb.name
            template = custom_template.replace("{query}", "[query]")
                                       .replace("{context}", "[context]")
                                       .replace("{kb_name}", kb.name)
        else:
            template = global_rag_template  # System setting
        # Inject into messages
        messages = apply_template(template, query=query, context=retrieved_docs)
```

### 8.3 Variable Substitution

| Template Variable | Runtime Value |
|---|---|
| `{query}` | User's chat message |
| `{context}` | Retrieved documents concatenated |
| `{kb_name}` | Knowledge base display name |

---

## 9. Trade-offs & Decisions

### 9.1 SSE vs WebSocket

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| SSE | Simple, HTTP-native, auto-reconnect | Unidirectional | ✅ Chosen |
| WebSocket | Bidirectional | More complex, needs infrastructure | ❌ |
| Polling only | Simplest | Higher latency, more requests | Fallback only |

**Decision**: SSE as primary channel + 3s polling as fallback. This gives low latency in the happy path and guaranteed delivery when SSE fails (browser limits, proxies, etc.).

### 9.2 Snapshot Storage: Full Content vs References

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| Store full text | Complete restore | Storage bloat, duplicate content | ❌ |
| Store references + hashes | Lightweight, fast | Requires files to still exist | ✅ Chosen |

**Decision**: Store file_id references + content hashes. This keeps snapshots small and fast. The "Unlink Only" button mitigates the risk of file deletion breaking rollbacks.

### 9.3 Prompt Template: New Table vs Meta JSON

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| New `knowledge_prompt` table | Normalized, queryable | Schema migration, over-engineering | ❌ |
| `knowledge.meta` JSON | Zero migration, flexible | Not queryable via SQL | ✅ Chosen |

**Decision**: Store in `meta` JSON. One template per KB is sufficient; no need for querying across templates.

### 9.4 Chunk Persistence

Chunks are stored in both ChromaDB (vectors) and SQLite (metadata). This duplication enables:
- Fast metadata queries (chunk index, content hash, token count) without touching ChromaDB
- Independent reindexing (delete ChromaDB collection, rebuild from SQLite chunks)
- Snapshot comparison via content hashes

---

## 10. Testing Strategy

### 10.1 Integration Tests

All 26 new endpoints were verified with Python integration tests:

```python
# Example: chunk preview test
def test_preview_chunks():
    response = client.post(f"/api/v1/knowledge/{kb_id}/chunks/preview",
                          json={"file_id": file_id})
    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) > 0
    assert all("content" in c and "chunk_index" in c for c in chunks)
```

### 10.2 Build Validation

```bash
npm run build  # Frontend: SvelteKit compilation
python -c "import open_webui"  # Backend: all imports resolve
```

### 10.3 Manual E2E Test Flow

1. Create a knowledge base
2. Upload a document → verify it auto-processes
3. Navigate to Chunks tab → preview chunks → merge two → split one → reindex
4. Upload 3 more files → switch to Processing tab → observe real-time progress
5. Go to Evaluate → enter a query → annotate results → verify recall/precision/MRR
6. Create a snapshot → add a file → rollback → verify state restored
7. "Unlink Only" a file → verify it's removed from KB but still exists
8. Edit prompt template → send a chat message → verify template is used

### 10.4 Edge Cases Tested

- Empty knowledge base (no files) → Chunks tab shows "No files yet"
- Very long chunk content (10K+ characters) → View modal handles it
- Rapid file uploads → Processing dashboard correctly shows concurrent tasks
- Network interruption → Polling fallback engages after SSE disconnect
- Snapshot with deleted files → Rollback gracefully reports missing files

---

## Appendix: File Change Summary

| File | Change | Phase |
|---|---|---|
| `backend/open_webui/models/knowledge.py` | Modified | 1 (5 new model classes) |
| `backend/open_webui/routers/knowledge.py` | Modified | 1-6 (26 endpoints + progress hooks) |
| `backend/open_webui/routers/files.py` | Modified | 2 (upload pipeline progress hooks) |
| `backend/open_webui/utils/middleware.py` | Modified | 6 (prompt template injection) |
| `backend/open_webui/migrations/versions/a7b8c9d0e1f2_*.py` | New | 1 (Alembic migration) |
| `src/routes/(app)/workspace/knowledge/[id]/+layout.svelte` | New | 5 (tab navigation) |
| `src/routes/(app)/workspace/knowledge/[id]/+page.svelte` | Modified | 1-5 (files view) |
| `src/routes/(app)/workspace/knowledge/[id]/chunks/+page.svelte` | New | 1 |
| `src/routes/(app)/workspace/knowledge/[id]/processing/+page.svelte` | New | 2 |
| `src/routes/(app)/workspace/knowledge/[id]/evaluate/+page.svelte` | New | 3 |
| `src/routes/(app)/workspace/knowledge/[id]/snapshots/+page.svelte` | New | 4 |
| `src/lib/components/workspace/Knowledge/ChunkManager.svelte` | New | 1 |
| `src/lib/components/workspace/Knowledge/ProcessingDashboard.svelte` | New | 2 |
| `src/lib/components/workspace/Knowledge/EvaluatePanel.svelte` | New | 3, 6 |
| `src/lib/components/workspace/Knowledge/SnapshotManager.svelte` | New | 4 |
| `src/lib/components/workspace/Knowledge/KnowledgeBase.svelte` | Modified | 4 (Unlink Only button) |
| `src/lib/components/workspace/Knowledge/Files.svelte` | Modified | 4 |
| `src/lib/apis/knowledge/index.ts` | Modified | 1-4 (API client functions) |
