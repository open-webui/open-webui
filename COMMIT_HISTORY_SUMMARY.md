# Commit History Summary: redis-logging-enhancements Branch

## Overview
Complete itemized list of all changes since branch creation, organized chronologically (oldest to newest).

---

## 1. Redis Infrastructure & Connection Pooling
- **Add Redis to Dev environment** - Implemented connection pooling, added redis-deployment-info to .gitignore
- **Redis error handling** - Added comprehensive error handling and NYC timezone logging configuration
- **Redis Sentinel support** - Implemented Redis Sentinel for higher availability
- **Redis connection pooling** - Centralized connection pool management via get_redis_pool() across all modules

## 2. Portkey SDK Integration & Embeddings
- **Organize Portkey SDK documentation** - Moved evaluation files to .portkey sdk/ hidden folder
- **Portkey SDK embeddings implementation** - Migrated from HTTP to official Python SDK with user-specific virtual keys
- **User-specific virtual key management** - Implemented UserScopedConfig for per-admin virtual keys with group inheritance
- **Super admin email management** - Centralized via SUPER_ADMIN_EMAILS env var, added /users/super-admin-emails API endpoint
- **Frontend super admin updates** - Removed hardcoded emails, fetch from backend API in Settings/Documents/Knowledge/Prompts/Tools
- **Portkey embedding fixes** - Updated to match SDK tutorial, removed deprecated virtual_key parameter
- **Per-admin embedding API key** - Converted RAG_OPENAI_API_KEY to UserScopedConfig (per-admin, not global)
- **Dynamic per-user API key retrieval** - Fixed critical bug where embedding function used startup key instead of user's configured key
- **Embedding API key fixes** - Removed hardcoded defaults, updated to @openai-embedding/text-embedding-3-small model
- **Portkey embedding worker integration** - Pass per-user embedding API key to worker jobs for RBAC compliance

## 3. Performance Optimizations
- **Database query optimization** - Fixed N+1 queries in knowledge bases and models endpoints, batch file metadata queries
- **Frontend parallelization** - Parallelize API calls using Promise.all() for models/banners/tools loading
- **ThreadPoolExecutor optimization** - Created module-level thread pool for RAG operations (avoid per-request creation)
- **Non-blocking cache stampede handling** - Replaced time.sleep() with immediate fallback in async contexts
- **Batch embedding generation** - Batch all query embeddings in single API call (1 call instead of N calls)
- **Parallel query processing** - Parallelize web search queries and RAG retrieval queries using asyncio.gather/ThreadPoolExecutor
- **Query processing optimization** - Sequential processing for single query-collection pairs, parallel for multiple

## 4. Redis Caching & Atomic Operations
- **Redis caching for authentication** - Implemented caching for user authentication (JWT) and API key lookups
- **Cache invalidation** - Added invalidation for user role updates, settings, and API key changes
- **Atomic Redis operations** - Implemented Lua scripts for atomic operations (atomic_set_dict_field, atomic_remove_dict_fields, atomic_remove_from_list)
- **Atomic update optimizations** - Fixed atomic_update_dict() to use optimistic locking (WATCH/MULTI/EXEC)
- **WebSocket atomic operations** - Updated handlers (connect, disconnect, usage) to use atomic methods
- **Redis race condition fixes** - Replaced non-atomic read-modify-write with atomic Lua scripts for USAGE_POOL and USER_POOL
- **Memory management** - Added default_ttl to RedisDict (1 hour sessions, 30 min usage), prevents unbounded growth
- **Redis fallback handling** - Added isinstance() checks for RedisDict, fallback to regular dict when Redis disabled

## 5. Distributed Job Queue (RQ) Implementation
- **RQ job queue implementation** - Replaced FastAPI BackgroundTasks with Redis Queue for distributed, fault-tolerant processing
- **Job queue files** - Created job_queue.py, file_processor.py, start_worker.py for worker management
- **Router modifications** - Updated retrieval.py, files.py, knowledge.py to use job queue instead of BackgroundTasks
- **Distributed locking** - Added RedisLock to prevent duplicate file processing across replicas
- **Job configuration** - Added ENABLE_JOB_QUEUE, JOB_TIMEOUT, JOB_MAX_RETRIES, JOB_RETRY_DELAY, JOB_RESULT_TTL, JOB_FAILURE_TTL env vars
- **Worker context fixes** - Enhanced embedding function initialization in MockState for worker context
- **Lock release timing** - Fixed lock release to occur AFTER job enqueueing (prevents race conditions)
- **RQ worker resource cleanup** - Added cleanup and OpenShift deployment configuration

## 6. Task Model & Configuration
- **Per-admin task config** - Converted task config from PersistentConfig to UserScopedConfig for per-admin settings
- **Group inheritance** - Admin settings automatically apply to their user group members
- **Gemini 2.5 Flash Lite auto-config** - Auto-set TASK_MODEL_EXTERNAL to @vertexai/gemini-2.5-flash-lite if user has access
- **Task feature toggles** - ENABLE_TITLE_GENERATION, ENABLE_TAGS_GENERATION, ENABLE_AUTOCOMPLETE_GENERATION, ENABLE_SEARCH_QUERY_GENERATION, ENABLE_RETRIEVAL_QUERY_GENERATION now per-admin
- **Model access validation** - Added validation to all task endpoints (title, tags, autocomplete, queries)
- **Frontend task model updates** - Auto-select Gemini 2.5 Flash Lite, disable toggles if model unavailable
- **Enforce Gemini Flash Lite** - Refactored to enforce Gemini Flash Lite for all task generation, removed configurable model selection
- **Task model access check fix** - Convert models list to dict for fast ID lookup in user_has_access_to_task_model()

## 7. RAG Improvements
- **RAG default top_k** - Changed default RAG_TOP_K from 4 to 10 for better context retrieval
- **RAG query expansion logging** - Added logging for query expansion generation, failures, and fallback usage
- **RAG diagnostics** - Added diagnostics for empty RAG results, log collection names, warn if collection doesn't exist
- **File processing blocking** - Block file processing early if no embedding API key configured
- **Query validation** - Added validation for empty queries, filter whitespace-only queries, validate embeddings are non-empty
- **Edge case handling** - Added handling for single query case, empty query-collection pairs, hybrid search edge cases

## 8. File Processing & Knowledge Base
- **File deletion fixes** - Implemented complete file cleanup (vector DB, SQL, physical files) with centralized utility
- **File cleanup utility** - Created file_cleanup.py with helper methods to find knowledge bases by file_id
- **Knowledge collection fixes** - Fixed remove_file_from_knowledge_by_id() to handle single/multiple collections
- **Critical content extraction bug** - Fixed bug where file content extraction was never reached for new files (collection_name always set)
- **Content extraction logic** - Restructured to check vector DB cache first, then file.data, then Loader extraction
- **Knowledge Collection upload UX** - Updated toast messages to accurately reflect processing status (queued/completed/error)
- **File status tracking** - Added file status tracking to detect transitions during polling

## 9. Redis Lock & Cache Bug Fixes
- **RedisLock method name fix** - Fixed acquire_lock() to aquire_lock() to match actual method name
- **SQL type casting fix** - Added explicit jsonb cast in COALESCE for PostgreSQL UPDATE query
- **Lock release logic** - Release lock if task successfully enqueued, even if status update failed
- **Missing lock release** - Added lock release in API key check failure path
- **Redis cache bugs** - Fixed API key reverse mapping cleanup when reassigned, pipeline performance bug in invalidate_group_member_users
- **Set TTL refresh** - Refresh Set TTL on every add operation to prevent premature expiration
- **Lock creation error handling** - Improved with Redis availability check
- **Critical indentation errors** - Fixed indentation errors in RedisLock and RedisDict constructors (prevented startup)
- **Lock ID mismatch handling** - Made release_lock() idempotent, enhanced Lua script to return 3 states (success/expired/mismatch)
- **Background task exception fix** - Fixed exception in periodic_usage_pool_cleanup, graceful exit with retry tolerance (max 3 failures)

## 10. Code Quality & Bug Fixes
- **Duplicate function name fix** - Renamed duplicate get_functions to export_functions in functions.py (line 41)
- **Unused import removal** - Removed unused os import from functions.py
- **Missing import fixes** - Added missing imports: get_task_model_id in tasks.py, Any in retrieval.py, Callable in retrieval.py
- **Indentation fixes** - Fixed indentation errors in retrieval.py, ollama.py, openai.py, functions.py, RedisLock class
- **Missing closing brace** - Added missing closing brace for MermaidStore class
- **Syntax error fixes** - Fixed orphaned else block in knowledge.py, removed after return statement
- **Parameter order fixes** - Fixed parameter order in FastAPI endpoints (background_tasks before optional parameters)
- **Error handling improvements** - Added defensive null check in get_function_models() to prevent AttributeError
- **Function signature restoration** - Restored get_task_model_id() to accept 4 parameters (model_id, task_model, task_model_external, models)

## 11. Mermaid Scalability Optimization
- **Mermaid optimization implementation** - Implemented caching and performance improvements with global initialization
- **Two-tier caching** - Memory LRU cache (100 entries) + IndexedDB persistence (5MB limit, 7-day TTL)
- **Cross-tab synchronization** - Implemented BroadcastChannel for cache synchronization across tabs
- **Lazy loading** - Implemented with IntersectionObserver (only render visible diagrams)
- **Debouncing** - Added 300ms debouncing for streaming content
- **Error recovery** - Automatic retry with exponential backoff
- **Performance metrics** - <1ms cached, <20ms IndexedDB, <200ms uncached
- **Mermaid version update** - Updated to 11.12.2 (pinned)
- **Test suite** - Added comprehensive test suite (38 tests passing)
- **Build fixes** - Multiple fixes for package-lock.json, dependency resolution, Alpine Linux builds
- **Mermaid service initialization** - Fixed 'Mermaid service unavailable' error by initializing in app layout

## 12. OpenTelemetry (OTEL) Implementation
- **Phase 1: Foundation setup** - Added OTEL dependencies, created otel_config.py, integrated into FastAPI lifespan
- **Phase 2: Verification** - Verified Phase 1 initialization works correctly, confirmed error handling
- **Phase 3: Auto-instrumentation** - Added FastAPI and HTTP auto-instrumentation with configurable path exclusions
- **Phase 4A: Instrumentation helpers** - Created otel_instrumentation.py with reusable helper functions (trace_span, trace_span_async, trace_function, etc.)
- **Phase 4B: LLM call instrumentation** - Instrumented generate_chat_completion, OpenAI router, Ollama router, function/pipe completion
- **Phase 4C: File processing instrumentation** - Instrumented add_file_to_knowledge_by_id, save_docs_to_vector_db, get_embeddings_with_fallback
- **Phase 4D: RQ background jobs instrumentation** - Instrumented enqueue_file_processing_job, process_file_job with trace context propagation
- **Phase 5: Loguru trace correlation** - Modified stdout_format() and AuditLogger.write() to include trace_id and span_id
- **Phase 6: OTEL Collector sidecar** - Created otel-collector-config.yaml, updated webui-deployment.yaml and rq-worker-deployment.yaml
- **OTEL safety wrappers** - Added safe wrapper functions (safe_add_span_event, safe_set_span_attribute, safe_trace_span, safe_trace_span_async)
- **OTEL failure handling** - Ensured OTEL failures never block task execution (92+ calls wrapped across codebase)
- **Generator exception handling** - Fixed 'generator didn't stop after throw()' errors in all trace_span_async fallbacks
- **OTEL async context manager fixes** - Fixed safe_trace_span_async to return context manager (not coroutine)
- **OTEL API fixes** - Fixed PeriodicExportingMetricReader API usage, FastAPI instrumentation excluded_urls format
- **OTEL deployment guide** - Added comprehensive deployment guide for 7 phases

## 13. Logging & Timezone
- **NYC timezone logging** - Configured logging to use America/New_York timezone instead of GMT
- **Custom NYCFormatter** - Added for worker process to ensure NYC timezone in worker logs
- **Timezone early setup** - Set TZ environment variable early in logger.py before any logging operations

## 14. Security Fixes
- **Hardcoded password removal** - Removed hardcoded Redis passwords from QUICK_DEPLOY_CHECKLIST.md, DEPLOYMENT_READY_SUMMARY.md, OPENSHIFT_RQ_WORKER_DEPLOYMENT.md
- **Secrets removal** - Replaced hardcoded passwords with placeholders, added instructions to get from Kubernetes secrets
- **Local file security** - Removed local Docker compose file, fixed hardcoded paths, added local-only files to .gitignore
- **Super admin email security** - Removed hardcoded superadmin emails, require SUPER_ADMIN_EMAILS env var (no fallback defaults)

## 15. Frontend Bug Fixes
- **Race condition fixes** - Fixed race conditions in Knowledge, Prompts, and Tools components (Assign To dropdown)
- **Boolean/function call bugs** - Fixed in Settings and Documents components
- **File upload permission checks** - Fixed in MessageInput components
- **Admin Interface title generation** - Fixed markup generation
- **Switch component** - Added disabled state support for task features

## 16. Configuration & Environment
- **REDIS_MAX_CONNECTIONS** - Added default fallback (100), made import more robust with exception handling
- **Default super admin email** - Added default (ms15138@nyu.edu) if SUPER_ADMIN_EMAILS not set
- **Environment variable validation** - Added _safe_int_env() helper for robust integer parsing
- **Model detection improvements** - Added debug logging for available models and Gemini detection, flexible model ID format support

## 17. Documentation & Organization
- **Codebase improvements report** - Added report on codebase improvements for future reference
- **Performance analysis** - Added PERFORMANCE_ANALYSIS.md to .gitignore
- **Deployment checklists** - Added QUICK_DEPLOYMENT_CHECKLIST.md, QUICK_DEPLOYMENT_CHECKLIST.md
- **OTEL deployment guide** - Added comprehensive OTEL phases deployment guide
- **Manifest tracking** - Updated .gitignore with manifest tracking documentation
- **TODO updates** - Updated TODO.txt with job queue implementation completion status

## 18. Recent Debugging & Logging Fixes
- **Debug logging additions** - Added better logs to find errors in file processing
- **Log error fixes** - Fixed errors in logs and logical fixes
- **Double log issue** - Fixed duplicate logging issue
- **Model debug logging** - Added debug logging for model issues

---

## Summary Statistics
- **Total Commits**: 120+
- **Major Features**: Redis infrastructure, Portkey SDK, RQ job queue, OpenTelemetry, Mermaid optimization
- **Critical Bug Fixes**: File content extraction, embedding API key retrieval, generator exception handling, Redis race conditions
- **Performance Improvements**: Batch embeddings, parallel query processing, database query optimization, atomic Redis operations
- **Security Enhancements**: Removed hardcoded passwords, per-admin API keys, super admin email management
- **Code Quality**: Fixed indentation errors, duplicate functions, missing imports, syntax errors

---

*Generated from git log analysis of redis-logging-enhancements branch*


