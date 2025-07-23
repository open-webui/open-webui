# OpenRouter Model Filtering Debug Findings

## Summary

After investigating the OpenRouter model filtering issue in mAI (Open WebUI), I've identified how the system works and added debugging to help diagnose why filtering might not be applying correctly.

## How Model Filtering Works

1. **Configuration Storage**: The `OPENAI_API_CONFIGS` is stored in the database under the key `openai.api_configs` as a JSON object with string indices.

2. **Model Filtering Logic** (in `backend/open_webui/routers/openai.py`):
   - When `model_ids` is empty: Fetches all models from the API
   - When `model_ids` contains wildcards (`*` or `?`): Fetches all models then filters using patterns
   - When `model_ids` contains exact IDs (no wildcards): Returns ONLY those exact models without API call

3. **The filtering happens in `get_all_models_responses()`**:
   ```python
   if len(model_ids) == 0:
       # Fetch all models
   elif has_wildcards(model_ids):
       # Fetch all models, then filter
   else:
       # Return only the exact model IDs specified
   ```

## Debugging Added

I've added logging to help diagnose the issue:

1. **In `backend/open_webui/main.py`**:
   - Logs OpenAI configuration at startup
   - Shows all API URLs and their configurations

2. **In `backend/open_webui/routers/openai.py`**:
   - Logs when processing each connection's config
   - Shows model IDs being used
   - Logs model counts before/after filtering

## Common Issues & Solutions

### Issue 1: Configuration Not Persisting
**Symptom**: Model IDs are set but all models still show up

**Possible Causes**:
1. Configuration saved with wrong index type (should be string, not integer)
2. Database not updating properly
3. Cached configuration in memory

**Solutions**:
1. Use the `fix_openrouter_config.py` script to ensure proper configuration
2. Restart the backend after configuration changes
3. Check logs for the configuration being loaded

### Issue 2: Models Still Showing After Configuration
**Symptom**: Configuration looks correct but all models appear

**Possible Causes**:
1. Browser caching the model list
2. Frontend not refreshing after configuration change
3. Multiple OpenRouter connections configured

**Solutions**:
1. Clear browser cache completely
2. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
3. Check that only one OpenRouter connection exists

### Issue 3: Wrong Index Being Used
**Symptom**: Configuration exists but not being applied

**Possible Causes**:
1. OpenRouter URL at different index than expected
2. Legacy configuration format being used

**Solutions**:
1. Run `diagnose_openrouter.py` to see actual indices
2. Ensure configuration uses string indices (e.g., "0", "1", not 0, 1)

## Diagnostic Tools Created

### 1. `test_openrouter_config.py`
Tests the configuration via API and shows:
- Current configuration
- Model IDs configured
- Actual models returned
- Whether filtering is working

### 2. `diagnose_openrouter.py`
Checks the database directly:
- Shows stored configuration
- Displays model_ids for each connection
- Checks environment variables

### 3. `fix_openrouter_config.py`
Automatically fixes the configuration:
- Finds OpenRouter connection
- Updates with the 12 allowed models
- Verifies the fix worked

## How to Debug

1. **Check Backend Logs**:
   ```bash
   # Look for these log messages:
   "=== OpenAI Configuration at Startup ==="
   "OpenRouter config for idx X: enable=True, model_ids=[...]"
   "Using exact model IDs for idx X: [...]"
   ```

2. **Run Diagnostic Script**:
   ```bash
   python diagnose_openrouter.py
   ```

3. **Test via API**:
   ```bash
   python test_openrouter_config.py
   ```

4. **Fix if Needed**:
   ```bash
   python fix_openrouter_config.py
   ```

## Expected Behavior

When properly configured with exact model IDs:
1. NO API call is made to OpenRouter to fetch models
2. Only the specified model IDs are returned
3. The models appear instantly (no loading delay)

## Verification Steps

1. After configuration, check backend logs for:
   ```
   Using exact model IDs for idx 0: ['anthropic/claude-sonnet-4', ...]
   ```

2. In the UI, the model dropdown should show exactly 12 models

3. No network request to OpenRouter should occur when opening the model dropdown

## Next Steps

If model filtering still isn't working after following this guide:

1. Check the backend logs for the exact configuration being loaded
2. Verify the database has the correct configuration using `diagnose_openrouter.py`
3. Ensure you're modifying the correct OpenRouter connection (check the index)
4. Make sure to restart the backend and clear browser cache after changes

The debugging logs added will help identify exactly where the issue is occurring.