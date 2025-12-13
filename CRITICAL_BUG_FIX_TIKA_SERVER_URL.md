# Critical Bug Fix: KeyError 'TIKA_SERVER_URL'

## Problem

The RQ worker was failing to process file embedding jobs with the following error:

```
KeyError: 'TIKA_SERVER_URL'
```

### Root Cause

The `AppConfig.__getattr__` method in `backend/open_webui/config.py` raises a `KeyError` when accessing a config attribute that doesn't exist in `_state`. When `getattr(request.app.state.config, 'TIKA_SERVER_URL', None)` is called, Python's `getattr()` tries to access the attribute, which calls `__getattr__()`, which raises `KeyError` **before** `getattr()` can return the default value.

### Error Location

**File:** `backend/open_webui/workers/file_processor.py`  
**Lines:** 901, 725, 929

**Code that failed:**
```python
tika_url = getattr(request.app.state.config, 'TIKA_SERVER_URL', None) or os.environ.get('TIKA_SERVER_URL', '')
```

**Error:**
```python
File "/app/backend/open_webui/config.py", line 508, in __getattr__
    config_obj = self._state[key]
                 ~~~~~~~~~~~^^^^^
KeyError: 'TIKA_SERVER_URL'
```

### Impact

- **All file processing jobs were failing silently**
- Jobs were enqueued to Redis successfully
- Worker picked up jobs but crashed immediately
- No embeddings were generated
- Files appeared to be "processing" but never completed

---

## Solution

Use `hasattr()` to check if the attribute exists before calling `getattr()`. This prevents the `KeyError` from being raised.

### Fixed Code

**Before:**
```python
tika_url = getattr(request.app.state.config, 'TIKA_SERVER_URL', None) or os.environ.get('TIKA_SERVER_URL', '')
```

**After:**
```python
tika_url = (getattr(request.app.state.config, 'TIKA_SERVER_URL', None) if hasattr(request.app.state.config, 'TIKA_SERVER_URL') else None) or os.environ.get('TIKA_SERVER_URL', '')
```

### Files Fixed

1. **`backend/open_webui/workers/file_processor.py`** - Line 901
   - Fixed `TIKA_SERVER_URL` access
   - Fixed `PDF_EXTRACT_IMAGES` access
   - Fixed `DOCUMENT_INTELLIGENCE_ENDPOINT` access
   - Fixed `DOCUMENT_INTELLIGENCE_KEY` access
   - Fixed `CONTENT_EXTRACTION_ENGINE` access

2. **Multiple locations in the same file:**
   - Line 725 (in try/except block)
   - Line 929 (in another code path)

---

## Testing

After the fix:

1. **Restart the worker:**
   ```bash
   docker restart open-webui-app
   ```

2. **Upload a file and watch logs:**
   ```bash
   docker logs -f open-webui-app | grep -E "\[JOB|\[STEP|❌|✅"
   ```

3. **Check worker logs:**
   ```bash
   docker exec open-webui-app cat /tmp/rq-worker.log | tail -50
   ```

4. **Verify embeddings are created:**
   - File should process successfully
   - No `KeyError: 'TIKA_SERVER_URL'` errors
   - Embeddings should be generated and stored

---

## Why This Happened

The `AppConfig` class uses `__getattr__` to access configuration values. When a key doesn't exist in `_state`, it raises a `KeyError`. Python's `getattr()` function with a default value doesn't catch `KeyError` - it only catches `AttributeError`.

The proper fix would be to modify `AppConfig.__getattr__` to raise `AttributeError` instead of `KeyError`, or to check if the key exists first. However, using `hasattr()` is a safe workaround that doesn't require changing the config class.

---

## Related Issues

This same pattern might exist elsewhere in the codebase. Any code that uses:
```python
getattr(request.app.state.config, 'SOME_CONFIG', default)
```

where `SOME_CONFIG` might not exist in `_state` will fail with the same error.

**Recommendation:** Search for all uses of `getattr(request.app.state.config, ...)` and ensure they use `hasattr()` first, or fix `AppConfig.__getattr__` to handle missing keys properly.

---

## Status

✅ **FIXED** - All instances in `file_processor.py` have been updated.

---

## Next Steps

1. Test file upload and processing
2. Monitor worker logs for any other similar errors
3. Consider fixing `AppConfig.__getattr__` to raise `AttributeError` instead of `KeyError` for better compatibility with `getattr()`

