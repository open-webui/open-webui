# Retrieval Directive

> **Purpose:** Navigation protocol for Claude Code to efficiently find information in this codebase
> **Audience:** Claude Code and AI coding assistants
> **Usage:** Consult this document when you need to locate information or understand where to look

---

## Prerequisites

Before using this directive, ensure you have read:
- `PRODUCT_OVERVIEW.md` — Understanding of what Open WebUI does
- `DOCUMENTATION_INDEX.md` — Visual map of documentation structure

---

## Query Type Classification

When you receive a question or task, classify it into one of these types and follow the corresponding protocol.

### Type 1: Definition Questions

**Pattern:** "What is [term]?" | "What does [thing] mean?" | "Define [concept]"

**Protocol:**
1. **First:** Check `docs/DOMAIN_GLOSSARY.md` for the term
2. **If entity:** Check `docs/DATA_MODEL.md` for relationships and lifecycle
3. **If database field:** Check `docs/DATABASE_SCHEMA.md` for field details
4. **If not found:** Search code for type definitions, then comments

**Example:**
```
User: "What is a Knowledge Base?"
→ Read DOMAIN_GLOSSARY.md, find "Knowledge" entry
→ Read DATA_MODEL.md for Knowledge entity relationships
```

---

### Type 2: Implementation Questions

**Pattern:** "How do I [action]?" | "How should I [task]?" | "Add [feature]"

**Protocol:**
1. **First:** Check `docs/directives/` for matching `DIRECTIVE_*.md`
2. **Follow directive:** Each directive has Structural Pattern → Illustrative Application → Transfer Prompt
3. **If no directive:** Check `docs/ARCHITECTURE_OVERVIEW.md` for patterns
4. **Reference code:** Use file paths from directive to examine existing implementations

**Directive Selection Guide:**

| Task | Directive |
|------|-----------|
| New API endpoint | `DIRECTIVE_adding_api_router.md` |
| New LLM provider | `DIRECTIVE_adding_llm_provider.md` |
| Database schema change | `DIRECTIVE_database_migration.md` |
| Frontend state management | `DIRECTIVE_creating_svelte_store.md` |
| Frontend API client | `DIRECTIVE_adding_frontend_api.md` |
| New document type for RAG | `DIRECTIVE_adding_rag_loader.md` |
| Real-time WebSocket feature | `DIRECTIVE_adding_websocket_event.md` |
| Tool or function | `DIRECTIVE_adding_tool_function.md` |
| OAuth provider | `DIRECTIVE_adding_oauth_provider.md` |
| Admin panel feature | `DIRECTIVE_adding_admin_feature.md` |
| Backend tests | `DIRECTIVE_writing_backend_tests.md` |
| Frontend tests | `DIRECTIVE_writing_frontend_tests.md` |

---

### Type 3: Rationale Questions

**Pattern:** "Why is [thing] designed this way?" | "Why does [behavior] happen?" | "What was the reasoning for [decision]?"

**Protocol:**
1. **First:** Search `docs/adr/` for relevant ADR
2. **Check title keywords:** ADRs are named `ADR_NNN_[topic].md`
3. **Read Context and Decision sections** in the ADR
4. **If no ADR:** Check git history with `git log --grep="[keyword]"`

**ADR Quick Reference:**

| Topic | ADR |
|-------|-----|
| Why FastAPI? | `ADR_001_fastapi_backend.md` |
| Why SvelteKit? | `ADR_002_sveltekit_frontend.md` |
| Why multi-provider LLM? | `ADR_003_multi_provider_llm.md` |
| Why SQLAlchemy? | `ADR_004_sqlalchemy_multi_db.md` |
| Why Socket.IO? | `ADR_005_socketio_realtime.md` |
| Why this RAG design? | `ADR_006_rag_architecture.md` |
| Why this auth approach? | `ADR_007_auth_strategy.md` |
| Why message analytics table? | `ADR_008_message_analytics.md` |
| Why OpenAI Responses API? | `ADR_009_openai_responses_api.md` |
| Why these query optimizations? | `ADR_010_query_optimization.md` |
| Why playground architecture? | `ADR_011_playground_architecture.md` |
| Why Redis cluster? | `ADR_012_redis_cluster_otel.md` |
| Why user data controls? | `ADR_013_user_data_controls.md` |

---

### Type 4: Debugging Questions

**Pattern:** "Why isn't [thing] working?" | "[Error] when [action]" | "Bug in [feature]"

**Protocol:**
1. **First:** Read `docs/SYSTEM_TOPOLOGY.md` to understand the data flow
2. **Identify layer:** Is this frontend, backend API, database, or external service?
3. **Trace the flow:**
   - Frontend → `src/lib/apis/` (API client) → `src/lib/stores/` (state)
   - Backend → `backend/open_webui/routers/` (endpoint) → `backend/open_webui/models/` (data)
4. **Check error handling:** Look for try/catch, error responses in the relevant layer

**Layer Identification:**

| Symptom | Likely Layer | Start Here |
|---------|--------------|------------|
| UI not updating | Frontend store | `src/lib/stores/index.ts` |
| API returns error | Backend router | `backend/open_webui/routers/` |
| Data not persisting | Database model | `backend/open_webui/models/` |
| Auth failing | Auth utils | `backend/open_webui/utils/auth.py` |
| WebSocket disconnect | Socket handler | `backend/open_webui/socket/main.py` |
| RAG not retrieving | Retrieval service | `backend/open_webui/retrieval/` |

---

### Type 5: Testing Questions

**Pattern:** "How do I test [feature]?" | "What tests exist for [thing]?" | "Write tests for [component]"

**Protocol:**
1. **First:** Read `docs/TESTING_STRATEGY.md` for philosophy and coverage targets
2. **Backend tests:** Read `docs/directives/DIRECTIVE_writing_backend_tests.md`
3. **Frontend tests:** Read `docs/directives/DIRECTIVE_writing_frontend_tests.md`
4. **Find existing tests:** Look in `tests/` directory mirroring source structure

**Test Location Patterns:**

| Source File | Test Location |
|-------------|---------------|
| `backend/open_webui/routers/chats.py` | `tests/unit/routers/test_chats.py` |
| `backend/open_webui/models/users.py` | `tests/unit/models/test_users.py` |
| `src/lib/stores/index.ts` | `tests/unit/stores/index.test.ts` |
| `src/lib/components/Chat.svelte` | `tests/unit/components/Chat.test.ts` |

---

### Type 6: Architecture Questions

**Pattern:** "How does [system] work?" | "What's the architecture of [feature]?" | "Explain [subsystem]"

**Protocol:**
1. **First:** Read `docs/ARCHITECTURE_OVERVIEW.md` for component hierarchy
2. **For runtime behavior:** Read `docs/SYSTEM_TOPOLOGY.md`
3. **For specific subsystem:** Check relevant ADR
4. **Trace code:** Start from entry points listed in `PRODUCT_OVERVIEW.md`

**Entry Points:**

| Subsystem | Entry Point |
|-----------|-------------|
| Backend application | `backend/open_webui/main.py` |
| Frontend application | `src/routes/+layout.svelte` |
| WebSocket server | `backend/open_webui/socket/main.py` |
| RAG pipeline | `backend/open_webui/retrieval/` |
| Authentication | `backend/open_webui/routers/auths.py` |
| LLM proxy | `backend/open_webui/routers/openai.py` |

---

## Document Precedence Rules

When information conflicts between documents:

1. **Code is truth** when docs are stale (check git timestamps)
2. **Newer ADR supersedes older** when decisions conflict
3. **Directive > Architecture doc** for specific implementation details
4. **Comments in code > external docs** for implementation-level details
5. **DATABASE_SCHEMA.md** is generated — always accurate for schema

---

## Claude Code-Specific Guidance

### Before Starting Any Task

1. **Read `PRODUCT_OVERVIEW.md`** if you haven't in this session
2. **Classify the question type** using the patterns above
3. **Follow the protocol** for that question type
4. **Read referenced code files** before making changes

### File Reading Sequence for Common Tasks

**Adding a Backend Feature:**
```
1. docs/directives/DIRECTIVE_adding_api_router.md
2. backend/open_webui/routers/analytics.py (example)
3. backend/open_webui/main.py (registration)
4. docs/DATA_MODEL.md (if new entity)
```

**Adding a Frontend Feature:**
```
1. docs/directives/DIRECTIVE_creating_svelte_store.md
2. docs/directives/DIRECTIVE_adding_frontend_api.md
3. src/lib/stores/index.ts (example)
4. src/lib/apis/chats/index.ts (example)
```

**Debugging an Issue:**
```
1. docs/SYSTEM_TOPOLOGY.md
2. Identify the layer (frontend/backend/database)
3. Read relevant router/component/model
4. Check error handling in that layer
```

**Understanding Existing Code:**
```
1. docs/DOMAIN_GLOSSARY.md (terms used)
2. docs/DATA_MODEL.md (entity relationships)
3. docs/ARCHITECTURE_OVERVIEW.md (patterns)
4. Relevant ADR (rationale)
```

### Tool Usage Patterns

**Use Grep for:**
- Finding where a function is defined
- Locating all usages of a term
- Finding configuration values

**Use Glob for:**
- Finding files by pattern (e.g., `*.test.ts`)
- Locating all files in a directory
- Finding files by naming convention

**Use Read for:**
- Understanding file contents
- Checking implementation details
- Verifying documentation accuracy

**Use Task/Explore for:**
- Open-ended codebase exploration
- Finding files across multiple locations
- Understanding patterns across the codebase

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY TYPE → DOCUMENT                        │
├─────────────────────────────────────────────────────────────────┤
│  "What is X?"           →  DOMAIN_GLOSSARY.md                  │
│  "How do I X?"          →  directives/DIRECTIVE_*.md           │
│  "Why is X this way?"   →  adr/ADR_*.md                        │
│  "X isn't working"      →  SYSTEM_TOPOLOGY.md                  │
│  "How do I test X?"     →  TESTING_STRATEGY.md                 │
│  "How does X work?"     →  ARCHITECTURE_OVERVIEW.md            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    TASK → FILE LOCATIONS                        │
├─────────────────────────────────────────────────────────────────┤
│  API endpoint      →  backend/open_webui/routers/              │
│  Database model    →  backend/open_webui/models/               │
│  Database migration→  backend/open_webui/migrations/versions/  │
│  WebSocket event   →  backend/open_webui/socket/main.py        │
│  RAG loader        →  backend/open_webui/retrieval/loaders/    │
│  Frontend route    →  src/routes/                              │
│  Frontend store    →  src/lib/stores/index.ts                  │
│  Frontend API      →  src/lib/apis/                            │
│  Frontend component→  src/lib/components/                      │
│  Configuration     →  backend/open_webui/config.py             │
│  Environment vars  →  backend/open_webui/env.py                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

- `DOCUMENTATION_INDEX.md` — Complete document inventory
- `PRODUCT_OVERVIEW.md` — Codebase entry point
- `ARCHITECTURE_OVERVIEW.md` — System design details

---

*Last updated: 2026-02-03*
