# Model Visibility Issue Report - User Olaf

## Executive Summary

User Olaf (email: krokodylek1981@gmail.com) cannot see any models despite the administrator having access to 12 business models. The root cause is that **OpenRouter models are not registered in the Models database table**, which is required for the access control system to work.

## Root Cause Analysis

### 1. How Model Access Works in mAI

The model access flow in mAI works as follows:

1. **Model Retrieval**: When a user requests available models, the system calls `/api/models`
2. **Access Control**: For non-admin users, the system filters models through `get_filtered_models()`
3. **Database Check**: Each model is checked against the `model` table in the database
4. **Permission Verification**: Models are only shown if:
   - The model exists in the database
   - The user owns the model, OR
   - The model has public access (`access_control = NULL`), OR
   - The user has explicit read permissions

### 2. The Problem

The investigation revealed:

1. **No models in the database**: The `model` table is empty (0 records)
2. **Model filtering only works with registered models**: The `get_filtered_models()` function in `/backend/open_webui/routers/openai.py` filters out any model that doesn't exist in the database
3. **OpenRouter models are configured but not registered**: While the configuration specifies 12 OpenRouter models, they're not in the Models table

### 3. Code Analysis

From `/backend/open_webui/routers/openai.py` (lines 694-704):
```python
async def get_filtered_models(models, user):
    # Filter models based on user access control
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:  # Model must exist in database
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models
```

This code shows that models MUST exist in the database to be visible to users.

## Solution

I've created two scripts to diagnose and fix the issue:

### 1. Debug Script: `backend/debug_user_olaf_models.py`

This script:
- Checks user information and role
- Verifies models in the database
- Inspects OpenRouter configuration
- Provides diagnostic information

### 2. Fix Script: `backend/register_openrouter_models.py`

This script registers all 12 OpenRouter models in the database with public access.

**Usage:**
```bash
# Check current state
python3 backend/register_openrouter_models.py --check-only

# Dry run (see what would be done)
python3 backend/register_openrouter_models.py --dry-run

# Actually register the models
python3 backend/register_openrouter_models.py
```

## Implementation Steps

1. **Run the registration script**:
   ```bash
   python3 backend/register_openrouter_models.py
   ```

2. **Verify the registration**:
   ```bash
   python3 backend/register_openrouter_models.py --check-only
   ```

3. **Restart the mAI application** to ensure changes are loaded

4. **Test with user account** to verify models are now visible

## Alternative Solutions

If the primary solution doesn't work:

1. **Enable BYPASS_MODEL_ACCESS_CONTROL**: This setting bypasses all model access checks
   - Can be enabled in admin settings
   - Makes all models visible to all users

2. **Update user role**: If user has "pending" role, update to "user":
   ```sql
   UPDATE user SET role = 'user' WHERE email = 'krokodylek1981@gmail.com';
   ```

3. **Custom access control**: Modify the registered models to have specific user/group permissions

## Prevention

To prevent this issue in the future:

1. **Initialization script**: Create an initialization script that runs on first deployment to register OpenRouter models
2. **Migration system**: Implement a database migration system to ensure required data is present
3. **Health check**: Add a health check that verifies models are properly registered
4. **Documentation**: Document the model registration requirement for new deployments

## Technical Details

The 12 OpenRouter models that need registration:
1. anthropic/claude-sonnet-4
2. google/gemini-2.5-flash
3. google/gemini-2.5-pro
4. deepseek/deepseek-chat-v3-0324
5. anthropic/claude-3.7-sonnet
6. google/gemini-2.5-flash-lite-preview-06-17
7. openai/gpt-4.1
8. x-ai/grok-4
9. openai/gpt-4o-mini
10. openai/o4-mini-high
11. openai/o3
12. openai/chatgpt-4o-latest

Each model is registered with:
- `access_control = NULL` (public access)
- `is_active = 1` (enabled)
- Proper metadata and parameters
- Admin user as owner

## Conclusion

The issue is a deployment/initialization problem where OpenRouter models are configured but not registered in the database. The provided scripts offer both diagnostic capabilities and a permanent fix for the issue.