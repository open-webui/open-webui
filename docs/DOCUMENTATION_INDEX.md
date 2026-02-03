# Documentation Index

> **Purpose:** Visual map of all documentation with quick lookup tables
> **Audience:** Developers, AI agents, contributors
> **Navigation:** Start here to find the right document for your task

---

## Visual Map: Five-Layer Documentation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: ORIENTATION                                                            │
│  "What is this codebase and where do I start?"                                  │
│                                                                                  │
│  ┌──────────────────┐   ┌────────────────────┐   ┌──────────────────────────┐  │
│  │ PRODUCT_OVERVIEW │   │ DOCUMENTATION_INDEX│   │ RETRIEVAL_DIRECTIVE      │  │
│  │ (root)           │   │ (this file)        │   │                          │  │
│  │                  │   │                    │   │                          │  │
│  │ Features, stack, │   │ Visual map of all  │   │ Claude Code navigation   │  │
│  │ business context │   │ documentation      │   │ protocol                 │  │
│  └──────────────────┘   └────────────────────┘   └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: SEMANTIC (Domain Understanding)                                        │
│  "What do these terms mean in this codebase?"                                   │
│                                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐│
│  │  DOMAIN_GLOSSARY   │  │    DATA_MODEL      │  │    DATABASE_SCHEMA         ││
│  │                    │  │                    │  │                            ││
│  │  43+ terms with    │  │  Entity relation-  │  │  Field-level reference     ││
│  │  business→code     │  │  ships, lifecycle  │  │  (generated from models)   ││
│  │  mapping           │  │  diagrams          │  │                            ││
│  └────────────────────┘  └────────────────────┘  └────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: PROCEDURAL (How-To Directives)                                         │
│  "How do I add/change/extend specific features?"                                │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         docs/directives/                                   │ │
│  │                                                                            │ │
│  │  DIRECTIVE_adding_api_router.md         (new FastAPI endpoints)           │ │
│  │  DIRECTIVE_adding_llm_provider.md       (new AI provider integration)     │ │
│  │  DIRECTIVE_database_migration.md        (Alembic schema changes)          │ │
│  │  DIRECTIVE_creating_svelte_store.md     (frontend state management)       │ │
│  │  DIRECTIVE_adding_frontend_api.md       (API client modules)              │ │
│  │  DIRECTIVE_adding_rag_loader.md         (document type support)           │ │
│  │  DIRECTIVE_adding_websocket_event.md    (real-time features)              │ │
│  │  DIRECTIVE_adding_tool_function.md      (tools and functions)             │ │
│  │  DIRECTIVE_adding_oauth_provider.md     (OAuth integration)               │ │
│  │  DIRECTIVE_adding_admin_feature.md      (admin panel features)            │ │
│  │  DIRECTIVE_writing_backend_tests.md     (pytest patterns)                 │ │
│  │  DIRECTIVE_writing_frontend_tests.md    (Vitest/Playwright patterns)      │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: RATIONALE (Why Decisions Were Made)                                    │
│  "Why does the architecture work this way?"                                     │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                           docs/adr/                                        │ │
│  │                                                                            │ │
│  │  FOUNDATIONAL DECISIONS                                                    │ │
│  │  ADR_001_fastapi_backend.md             (Python async framework choice)   │ │
│  │  ADR_002_sveltekit_frontend.md          (frontend framework choice)       │ │
│  │  ADR_003_multi_provider_llm.md          (LLM abstraction layer)           │ │
│  │  ADR_004_sqlalchemy_multi_db.md         (database strategy)               │ │
│  │  ADR_005_socketio_realtime.md           (real-time architecture)          │ │
│  │  ADR_006_rag_architecture.md            (retrieval augmented generation)  │ │
│  │  ADR_007_auth_strategy.md               (authentication approach)         │ │
│  │                                                                            │ │
│  │  RECENT DECISIONS (from commits)                                          │ │
│  │  ADR_008_message_analytics.md           (analytics subsystem)             │ │
│  │  ADR_009_openai_responses_api.md        (multi-format API support)        │ │
│  │  ADR_010_query_optimization.md          (N+1 elimination patterns)        │ │
│  │  ADR_011_playground_architecture.md     (AI playground subsystem)         │ │
│  │  ADR_012_redis_cluster_otel.md          (distributed infrastructure)      │ │
│  │  ADR_013_user_data_controls.md          (privacy and data governance)     │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: OPERATIONAL (System Behavior)                                          │
│  "How does the system actually work at runtime?"                                │
│                                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐│
│  │ARCHITECTURE_OVERVIEW│  │  SYSTEM_TOPOLOGY   │  │    TESTING_STRATEGY        ││
│  │                    │  │                    │  │                            ││
│  │  Component hier-   │  │  Data flows,       │  │  Test pyramid, coverage    ││
│  │  archy, patterns   │  │  service calls,    │  │  targets, integration      ││
│  │                    │  │  runtime behavior  │  │  boundaries                ││
│  └────────────────────┘  └────────────────────┘  └────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Lookup Table

| I need to... | Read this first | Then check |
|--------------|-----------------|------------|
| Understand what Open WebUI does | `PRODUCT_OVERVIEW.md` | — |
| Find the right documentation | `DOCUMENTATION_INDEX.md` (this file) | `RETRIEVAL_DIRECTIVE.md` |
| Understand a domain term | `DOMAIN_GLOSSARY.md` | `DATA_MODEL.md` |
| See database table structure | `DATABASE_SCHEMA.md` | `DATA_MODEL.md` |
| Add a new API endpoint | `DIRECTIVE_adding_api_router.md` | `backend/open_webui/routers/` |
| Integrate a new LLM provider | `DIRECTIVE_adding_llm_provider.md` | `ADR_003_multi_provider_llm.md` |
| Change the database schema | `DIRECTIVE_database_migration.md` | `DATA_MODEL.md` |
| Add frontend state | `DIRECTIVE_creating_svelte_store.md` | `src/lib/stores/` |
| Add a frontend API client | `DIRECTIVE_adding_frontend_api.md` | `src/lib/apis/` |
| Support a new document type | `DIRECTIVE_adding_rag_loader.md` | `ADR_006_rag_architecture.md` |
| Add real-time features | `DIRECTIVE_adding_websocket_event.md` | `ADR_005_socketio_realtime.md` |
| Create a tool or function | `DIRECTIVE_adding_tool_function.md` | `DOMAIN_GLOSSARY.md` (Tool, Function) |
| Add OAuth provider | `DIRECTIVE_adding_oauth_provider.md` | `ADR_007_auth_strategy.md` |
| Build admin features | `DIRECTIVE_adding_admin_feature.md` | `ARCHITECTURE_OVERVIEW.md` |
| Write backend tests | `DIRECTIVE_writing_backend_tests.md` | `TESTING_STRATEGY.md` |
| Write frontend tests | `DIRECTIVE_writing_frontend_tests.md` | `TESTING_STRATEGY.md` |
| Understand why X was built this way | `docs/adr/ADR_*.md` | `ARCHITECTURE_OVERVIEW.md` |
| Debug a data flow issue | `SYSTEM_TOPOLOGY.md` | `ARCHITECTURE_OVERVIEW.md` |

---

## AI Agent Context Table

For Claude Code and other AI assistants, this table maps task types to document reading sequences.

| Task Type | Primary Documents | Secondary | Code Reference |
|-----------|-------------------|-----------|----------------|
| **Bug fix (backend)** | `SYSTEM_TOPOLOGY.md` | `ARCHITECTURE_OVERVIEW.md` | `backend/open_webui/routers/` |
| **Bug fix (frontend)** | `SYSTEM_TOPOLOGY.md` | `ARCHITECTURE_OVERVIEW.md` | `src/lib/components/` |
| **New API endpoint** | `DIRECTIVE_adding_api_router.md` | `DATA_MODEL.md` | `backend/open_webui/routers/analytics.py` |
| **New LLM provider** | `DIRECTIVE_adding_llm_provider.md` | `ADR_003` | `backend/open_webui/routers/openai.py` |
| **Database change** | `DIRECTIVE_database_migration.md` | `DATA_MODEL.md` | `backend/open_webui/migrations/` |
| **Frontend feature** | `DIRECTIVE_creating_svelte_store.md` | `DIRECTIVE_adding_frontend_api.md` | `src/lib/stores/index.ts` |
| **RAG enhancement** | `DIRECTIVE_adding_rag_loader.md` | `ADR_006` | `backend/open_webui/retrieval/` |
| **WebSocket feature** | `DIRECTIVE_adding_websocket_event.md` | `ADR_005` | `backend/open_webui/socket/main.py` |
| **Auth change** | `DIRECTIVE_adding_oauth_provider.md` | `ADR_007` | `backend/open_webui/routers/auths.py` |
| **Test writing** | `TESTING_STRATEGY.md` | `DIRECTIVE_writing_*_tests.md` | `tests/` |
| **Performance issue** | `SYSTEM_TOPOLOGY.md` | `ADR_010` | Relevant router/service |
| **Understanding codebase** | `PRODUCT_OVERVIEW.md` | `ARCHITECTURE_OVERVIEW.md` | — |

---

## Document Inventory

### Layer 1: Orientation
| Document | Location | Purpose |
|----------|----------|---------|
| `PRODUCT_OVERVIEW.md` | `/PRODUCT_OVERVIEW.md` | Features, stack, entry point |
| `DOCUMENTATION_INDEX.md` | `/docs/DOCUMENTATION_INDEX.md` | Visual map, quick lookup |
| `RETRIEVAL_DIRECTIVE.md` | `/docs/RETRIEVAL_DIRECTIVE.md` | Claude Code navigation protocol |

### Layer 2: Semantic
| Document | Location | Purpose |
|----------|----------|---------|
| `DOMAIN_GLOSSARY.md` | `/docs/DOMAIN_GLOSSARY.md` | Business → code term mapping |
| `DATA_MODEL.md` | `/docs/DATA_MODEL.md` | Entity relationships, lifecycle |
| `DATABASE_SCHEMA.md` | `/docs/DATABASE_SCHEMA.md` | Field-level schema reference |

### Layer 3: Procedural
| Document | Location | Task |
|----------|----------|------|
| `DIRECTIVE_adding_api_router.md` | `/docs/directives/` | New FastAPI endpoints |
| `DIRECTIVE_adding_llm_provider.md` | `/docs/directives/` | LLM provider integration |
| `DIRECTIVE_database_migration.md` | `/docs/directives/` | Alembic migrations |
| `DIRECTIVE_creating_svelte_store.md` | `/docs/directives/` | Frontend state |
| `DIRECTIVE_adding_frontend_api.md` | `/docs/directives/` | API client modules |
| `DIRECTIVE_adding_rag_loader.md` | `/docs/directives/` | Document loaders |
| `DIRECTIVE_adding_websocket_event.md` | `/docs/directives/` | Real-time events |
| `DIRECTIVE_adding_tool_function.md` | `/docs/directives/` | Tools and functions |
| `DIRECTIVE_adding_oauth_provider.md` | `/docs/directives/` | OAuth integration |
| `DIRECTIVE_adding_admin_feature.md` | `/docs/directives/` | Admin features |
| `DIRECTIVE_writing_backend_tests.md` | `/docs/directives/` | pytest patterns |
| `DIRECTIVE_writing_frontend_tests.md` | `/docs/directives/` | Vitest/Playwright |

### Layer 4: Rationale
| Document | Location | Decision |
|----------|----------|----------|
| `ADR_001_fastapi_backend.md` | `/docs/adr/` | Python framework choice |
| `ADR_002_sveltekit_frontend.md` | `/docs/adr/` | Frontend framework |
| `ADR_003_multi_provider_llm.md` | `/docs/adr/` | LLM abstraction |
| `ADR_004_sqlalchemy_multi_db.md` | `/docs/adr/` | Database strategy |
| `ADR_005_socketio_realtime.md` | `/docs/adr/` | Real-time architecture |
| `ADR_006_rag_architecture.md` | `/docs/adr/` | RAG design |
| `ADR_007_auth_strategy.md` | `/docs/adr/` | Authentication |
| `ADR_008_message_analytics.md` | `/docs/adr/` | Analytics subsystem |
| `ADR_009_openai_responses_api.md` | `/docs/adr/` | API format support |
| `ADR_010_query_optimization.md` | `/docs/adr/` | N+1 patterns |
| `ADR_011_playground_architecture.md` | `/docs/adr/` | Playground design |
| `ADR_012_redis_cluster_otel.md` | `/docs/adr/` | Infrastructure |
| `ADR_013_user_data_controls.md` | `/docs/adr/` | Privacy controls |

### Layer 5: Operational
| Document | Location | Purpose |
|----------|----------|---------|
| `ARCHITECTURE_OVERVIEW.md` | `/docs/ARCHITECTURE_OVERVIEW.md` | System design |
| `SYSTEM_TOPOLOGY.md` | `/docs/SYSTEM_TOPOLOGY.md` | Runtime behavior |
| `TESTING_STRATEGY.md` | `/docs/TESTING_STRATEGY.md` | Test philosophy |

---

## Cross-Reference Rules

This documentation system follows these cross-reference patterns:

1. **Prerequisites section:** Required at document start. Lists documents that should be read first.
2. **Related Documents section:** Required at document end. Maximum 3-5 links.
3. **Inline links:** Prohibited except for external URLs or code file paths.
4. **Bidirectional references:** Not required. Use this index for reverse lookups.

---

## Maintenance

| Trigger | Action |
|---------|--------|
| New feature added | Update `PRODUCT_OVERVIEW.md`, create directive if pattern is reusable |
| New entity/table | Update `DOMAIN_GLOSSARY.md`, `DATA_MODEL.md`, regenerate `DATABASE_SCHEMA.md` |
| Architecture change | Create new ADR, update `ARCHITECTURE_OVERVIEW.md` |
| New pattern established | Create directive if task will recur |

See `DOCUMENTATION_LOG.md` for implementation progress and decisions.

---

*Last updated: 2026-02-03*
