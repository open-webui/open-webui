# Analysis: "Idle in Transaction" Database Connection Leaks in Open WebUI

## Executive Summary

The root cause of the "idle in transaction" PostgreSQL connection leaks has been identified. The primary issue is a **missing `ScopedSession.remove()` call** in the HTTP middleware, combined with several secondary patterns that exacerbate the problem.

## Root Cause Analysis

### Critical Issue 1: Middleware Missing Session Cleanup (HIGH PRIORITY)

**Location:** `backend/open_webui/main.py:1357-1362`

```python
@app.middleware("http")
async def commit_session_after_request(request: Request, call_next):
    response = await call_next(request)
    ScopedSession.commit()  # PROBLEM: No ScopedSession.remove()!
    return response
```

**Problem:**
When using SQLAlchemy's `scoped_session`:
- `commit()` commits the transaction but **keeps the session active**
- `remove()` is required to return the connection to the pool
- Without `remove()`, the connection stays "checked out" from the pool in an "idle in transaction" state

This is the **primary cause** of the observed behavior.

### Critical Issue 2: PgVector Uses Shared ScopedSession

**Location:** `backend/open_webui/retrieval/vector/dbs/pgvector.py:92-95`

```python
if not PGVECTOR_DB_URL:
    from open_webui.internal.db import ScopedSession
    self.session = ScopedSession
```

When `PGVECTOR_DB_URL` is not set (which is likely your configuration), pgvector uses the same `ScopedSession` as the main application. This means:
- Vector DB operations (embeddings, search) use the same session as HTTP requests
- After read operations: `rollback()` is called but not `remove()`
- After write operations: `commit()` is called but not `remove()`

### Critical Issue 3: WebSocket Handlers Lack Session Cleanup

**Location:** `backend/open_webui/socket/main.py`

WebSocket event handlers call model methods directly:

```python
@sio.event
async def connect(sid, environ, auth):
    user = Users.get_user_by_id(data["id"])  # Uses ScopedSession internally
```

WebSocket connections are long-lived (hours to days) and:
- Don't go through the HTTP middleware
- `ScopedSession.commit()` is never called
- `ScopedSession.remove()` is never called
- Connections accumulate over the lifetime of the WebSocket

### Critical Issue 4: Background Tasks Session Handling

**Location:** `backend/open_webui/routers/files.py:305-313`

```python
background_tasks.add_task(
    process_uploaded_file,
    request,
    file,
    file_path,
    file_item,
    file_metadata,
    user,
)  # No db session passed
```

Background tasks create their own sessions via `SessionLocal()`, which is correct. However, internal operations that use `ScopedSession` (like vector DB operations via pgvector) won't have their sessions cleaned up.

## Architecture Analysis

### Session Management Structure

```
db.py defines:
├── SessionLocal = sessionmaker(...)        # Factory for creating sessions
├── ScopedSession = scoped_session(...)     # Thread-local session registry
├── get_session()                           # Generator for FastAPI Depends()
├── get_db = contextmanager(get_session)    # Context manager wrapper
└── get_db_context(db)                      # Conditional session sharing
```

### Data Flow for File Queries

1. HTTP request arrives → middleware sets up context
2. Route handler calls `Files.get_file_by_id(id, db=db)`
3. `get_db_context(db)` either reuses session or creates new one
4. Query executes: `SELECT file.id ... FROM file`
5. Result returned, but session not properly closed
6. Middleware calls `ScopedSession.commit()` but NOT `remove()`
7. Connection stays "idle in transaction"

## Reproduction Hypothesis

The "idle in transaction" connections with `SELECT ... FROM file` queries likely occur during:

### Scenario 1: File Upload with Processing
1. User uploads file → HTTP request starts
2. Background task processes file → calls vector DB
3. Vector DB uses `ScopedSession` → same session as HTTP request
4. HTTP response returns → middleware commits but doesn't remove
5. Session stays bound with open transaction for 30-50+ minutes

### Scenario 2: WebSocket Activity
1. User connects via WebSocket
2. Events call models (`Users.get_user_by_id`, `Channels.get_channels_by_user_id`, etc.)
3. Models internally use `ScopedSession`
4. WebSocket stays open for hours
5. Sessions accumulate, never removed

### Scenario 3: SSE File Processing Status
1. Client streams file processing status via `/files/{id}/process/status?stream=true`
2. Every second, `Files.get_file_by_id(file_id)` is called
3. If underlying implementation touches `ScopedSession`, sessions accumulate

## Recommended Fixes

### Fix 1: Add ScopedSession.remove() to Middleware (CRITICAL)

**File:** `backend/open_webui/main.py`

```python
@app.middleware("http")
async def commit_session_after_request(request: Request, call_next):
    response = await call_next(request)
    try:
        ScopedSession.commit()
    finally:
        ScopedSession.remove()  # ADD THIS LINE
    return response
```

This is the **minimal fix** that addresses the immediate issue.

### Fix 2: PgVector Should Use Its Own Session Management

When `PGVECTOR_DB_URL` is not set, pgvector should create short-lived sessions for each operation instead of using the shared `ScopedSession`:

```python
# Instead of:
self.session = ScopedSession

# Use:
from open_webui.internal.db import get_db
# And wrap each operation in: with get_db() as session:
```

### Fix 3: WebSocket Session Cleanup

Add explicit session cleanup after model operations in WebSocket handlers, or ensure model methods don't use `ScopedSession` when called from non-HTTP contexts.

## Implementation Priority

1. **Immediate (P0):** Add `ScopedSession.remove()` to middleware
2. **Short-term (P1):** Refactor pgvector to use independent session management
3. **Medium-term (P2):** Add session cleanup to WebSocket handlers
4. **Long-term (P3):** Consider removing `ScopedSession` entirely in favor of explicit request-scoped sessions

## Verification Steps

After applying Fix 1:

1. Monitor `pg_stat_activity` for "idle in transaction" connections
2. Verify connection pool utilization normalizes
3. Check that connections are returned to pool after requests complete

Query to monitor:
```sql
SELECT pid, state, state_change, query, age(clock_timestamp(), state_change) as duration
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND application_name LIKE '%open_webui%'
ORDER BY state_change;
```

## Files Modified

- `backend/open_webui/main.py` - Added `ScopedSession.remove()` call
- `IDLE_TRANSACTION_ANALYSIS.md` - This analysis document
