# Logging Enhancements Summary

## Overview

Comprehensive logging and print statements have been added throughout the embedding pipeline to help debug critical bugs. All critical paths now have detailed step-by-step logging with clear markers.

---

## Files Modified

### 1. `backend/open_webui/workers/file_processor.py`

**Enhancements:**
- ✅ Added comprehensive logging to `initialize_embedding_function()` method
- ✅ Added step-by-step logging for API key validation
- ✅ Added logging for embedding function creation
- ✅ Added validation checks with clear error messages
- ✅ Enhanced `process_file_job()` with detailed input parameter logging
- ✅ Added API key validation before embedding function initialization

**Key Log Markers:**
- `[EMBEDDING INIT]` - Embedding function initialization
- `[STEP X]` - Step-by-step progress
- `✅` - Success markers
- `❌` - Error markers
- `⚠️` - Warning markers

---

### 2. `backend/open_webui/routers/retrieval.py`

**Enhancements:**
- ✅ Added comprehensive logging to `process_file()` endpoint
- ✅ Added API key retrieval and validation logging
- ✅ Enhanced `save_docs_to_vector_db()` with step-by-step logging
- ✅ Enhanced `save_docs_to_multiple_collections()` with step-by-step logging
- ✅ Added logging to `_process_file_sync()` for BackgroundTasks path
- ✅ Fixed undefined variable bug in `save_docs_to_multiple_collections` (line 1201)
- ✅ Fixed collection name bug in cache check (uses `collection_name` instead of `f"file-{file.id}"`)

**Key Log Markers:**
- `[PROCESS FILE]` - File processing request
- `[EMBEDDING]` - Embedding generation
- `[BACKGROUND TASK]` - Background task processing
- `[STEP X]` - Step-by-step progress
- `[CACHE CHECK]` - Vector DB cache check
- `✅` - Success markers
- `❌` - Error markers
- `⚠️` - Warning markers

---

## New Files Created

### 1. `view_logs.sh`

**Purpose:** Unified log viewer script for OpenWebUI and Redis/RQ workers

**Features:**
- Interactive menu for selecting log views
- Support for main app, worker, and Redis logs
- Color-coded output by log level
- Docker and Kubernetes support
- Custom log file location support

**Usage:**
```bash
# Interactive menu
./view_logs.sh

# View specific logs
./view_logs.sh main      # Main app only
./view_logs.sh worker    # Worker only
./view_logs.sh redis     # Redis only
./view_logs.sh all       # All logs interleaved
./view_logs.sh combined  # Main app + worker
```

---

### 2. `LOGGING_GUIDE.md`

**Purpose:** Comprehensive guide on where to find logs and how to use them

**Contents:**
- Log file locations for different deployment scenarios
- How to access logs in Docker, Kubernetes, and local environments
- Log format and markers explanation
- Debugging workflow
- Common error patterns and fixes
- Real-time monitoring tips
- Kubernetes and Docker-specific instructions

---

## Critical Bug Fixes Applied

### 1. API Key Validation

**Before:**
- API keys were not validated before use
- None/empty keys would cause silent failures

**After:**
- ✅ API keys are validated at multiple checkpoints
- ✅ Clear error messages when API key is None/empty
- ✅ Validation happens before embedding function creation
- ✅ Validation happens in both worker and main app paths

**Log Example:**
```
[STEP 1.2] API key retrieval result:
  embedding_api_key is None: False
  embedding_api_key length: 51
[STEP 1.3] ✅ API key retrieved and validated
```

---

### 2. Undefined Variable Bug Fix

**Location:** `save_docs_to_multiple_collections` (line 1201)

**Before:**
```python
log.info(
    f"Document with hash {metadata['hash']} already exists in collection {collection_name}"
)
# collection_name was undefined in this scope
```

**After:**
```python
collection_name_for_log = collections[1] if len(collections) > 1 else collections[0] if len(collections) > 0 else "unknown"
log.info(
    f"Document with hash {metadata['hash']} already exists in collection {collection_name_for_log}"
)
```

---

### 3. Wrong Collection Name in Cache Check

**Location:** `_process_file_sync` (line ~1710)

**Before:**
```python
result = VECTOR_DB_CLIENT.query(
    collection_name=f"file-{file.id}", filter={"file_id": file.id}
)
# Always used f"file-{file.id}" even when collection_name was provided
```

**After:**
```python
cache_collection = collection_name  # Use provided collection_name
result = VECTOR_DB_CLIENT.query(
    collection_name=cache_collection, filter={"file_id": file.id}
)
```

---

## Logging Patterns

### Success Pattern:
```
[STEP X] ✅ Operation completed successfully
```

### Error Pattern:
```
[STEP X] ❌ CRITICAL BUG: Error description
```

### Warning Pattern:
```
[STEP X] ⚠️  Warning message
```

### Step-by-Step Pattern:
```
[STEP 1] Description
  [STEP 1.1] Sub-step
  [STEP 1.2] Sub-step
[STEP 2] Next major step
```

---

## Where to Find Logs

### Main Application:
- **Docker:** `docker logs -f <container-name>`
- **Kubernetes:** `kubectl logs -f <pod-name>`
- **Local:** stdout/stderr or `/tmp/openwebui.log` (if redirected)

### Worker:
- **Docker:** `docker logs -f <worker-container-name>`
- **Kubernetes:** `kubectl logs -f <worker-pod-name>`
- **Local:** `/tmp/rq-worker.log` or stdout/stderr

### Redis:
- **Docker:** `docker logs -f <redis-container-name>`
- **Kubernetes:** `kubectl logs -f <redis-pod-name>`
- **Local:** `/var/log/redis/redis-server.log`

---

## Quick Debugging Workflow

1. **Check API Key Retrieval:**
   ```bash
   grep -i "api key.*none\|❌.*api key" <log-file>
   ```

2. **Check Embedding Generation:**
   ```bash
   grep -i "\[EMBEDDING\|\[STEP 6" <log-file>
   ```

3. **Check Worker Processing:**
   ```bash
   grep -i "\[JOB START\|\[STEP" <worker-log-file>
   ```

4. **Check Critical Bugs:**
   ```bash
   grep "CRITICAL BUG" <log-file>
   ```

5. **View All Logs Together:**
   ```bash
   ./view_logs.sh all
   ```

---

## Next Steps

1. **Test the logging:**
   - Upload a file and watch the logs
   - Verify all steps are logged
   - Check for any missing log points

2. **Use the logs to debug:**
   - Follow the step-by-step markers
   - Look for `❌` markers to find failures
   - Check API key validation steps

3. **Fix critical bugs:**
   - Use the logs to identify where bugs occur
   - Fix issues one by one
   - Verify fixes with logs

---

## Summary

✅ **Comprehensive logging added** to all critical paths
✅ **Print statements** for easy reading
✅ **Step-by-step markers** for debugging
✅ **API key validation** with clear error messages
✅ **Bug fixes** applied (undefined variable, wrong collection name)
✅ **Log viewer script** created for unified access
✅ **Documentation** created for log locations and usage

All logs are now easily accessible and provide clear visibility into the embedding pipeline at every step!

