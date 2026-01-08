# Model Visibility Bug - Root Cause Analysis

## Problem Statement
Users with role "user" can see ALL models created by ALL admins, when they should only see:
1. Models assigned to their group by their admin
2. Models they created themselves
3. **NOT** models created by other admins
4. **NOT** models created by other users

## Executive Summary

**5 Critical Bugs Identified:**

1. **Function/Pipe Models:** `(user.role == "user")` allows ALL users to see ALL pipes/functions
2. **External Models:** Portkey/OpenAI models not in database are auto-included without access check
3. **Database Query:** `get_functions_by_type()` returns ALL functions without filtering
4. **Default Access Control:** Models with `access_control=None` default to PUBLIC (visible to all users)
5. **Missing Group Check:** `item_assigned_to_user_groups()` not used in `get_all_models()` filtering

**Primary Root Cause:**
The filtering logic in `get_function_models()` incorrectly allows all users to see all function/pipe models, and external models (Portkey) are included without any access control checks. Additionally, models with `access_control=None` default to public visibility, meaning admins must explicitly set group assignments or models become visible to all users.

## Root Causes Identified

### BUG #1: Function/Pipe Models - Incorrect Filtering Logic
**Location:** `backend/open_webui/functions.py:158`

**Code:**
```python
if (user.role == "admin" and pipe.created_by == user.email) or (user.role == "user") or is_super_admin(user):
```

**Problem:**
- The condition `(user.role == "user")` evaluates to `True` for **ANY** user, regardless of who created the pipe
- This means ALL users see ALL pipes/functions from ALL admins
- The logic should check:
  - If user is admin: only show pipes created by that admin
  - If user is user: only show pipes assigned to their groups OR created by their admin (via group assignment)

**Impact:** Users see all function/pipe models (e.g., Portkey models) created by any admin.

---

### BUG #2: External Models (Portkey) Not Filtered
**Location:** `backend/open_webui/main.py:1183-1188`

**Code:**
```python
else:
    # Model not in database (e.g., Portkey/external models)
    # If model exists in models dict, it's available from external source (Portkey)
    # Include it since external models are dynamically fetched and don't need database entry
    # The fact that it's in the models dict means it's available to the user
    filtered_models.append(model)
```

**Problem:**
- External models (Portkey, OpenAI API models) that don't exist in the database are **automatically included** without any access control check
- The comment assumes "if it's in the models dict, it's available to the user" - this is **incorrect**
- These models should be filtered based on:
  - Group assignment (if the model was created via a function/pipe)
  - Admin ownership (if the model comes from an admin's function/pipe)

**Impact:** Users see all external models fetched from Portkey/OpenAI APIs, even if they weren't assigned to their groups.

---

### BUG #3: `get_functions_by_type` Returns ALL Functions Without Filtering
**Location:** `backend/open_webui/models/functions.py:156-171`

**Code:**
```python
def get_functions_by_type(self, type: str, active_only=False) -> list[FunctionModel]:
    with get_db() as db:
        if active_only:
            return [
                FunctionModel.model_validate(function)
                for function in db.query(Function)
                .filter_by(type=type, is_active=True)
                .all()
            ]
```

**Problem:**
- This method returns **ALL** functions of a given type from the database, regardless of who created them
- It's called in `get_function_models()` which then tries to filter, but the filtering logic is broken (see BUG #1)
- Should either:
  - Filter at the database level by `created_by` or group assignment, OR
  - Return all and filter properly in `get_function_models()`

**Impact:** All pipes/functions are fetched from the database, then incorrectly filtered, leading to users seeing all models.

---

### BUG #4: Custom Models May Not Respect Group Assignment for Users
**Location:** `backend/open_webui/utils/models.py:112-168`

**Code Flow:**
1. Line 112: `custom_models = Models.get_all_models(user.id, user.email)` - This correctly filters by `created_by` or `has_access`
2. Lines 113-168: Custom models are added to the models list

**Problem:**
- `Models.get_all_models()` filters correctly, BUT:
  - For users, it checks `model.created_by == user_email` OR `has_access(user_id, permission, model.access_control)`
  - The `has_access()` function checks group assignment, which is correct
  - However, the issue is that models created by Admin A might not have proper `access_control` set, OR the user might not be in the correct group
  - Need to verify: Are models created by admins properly setting `access_control` with group assignments?

**Impact:** If admins don't set `access_control` properly when creating models, users might see them OR not see them incorrectly.

---

### BUG #5: OpenAI/Ollama Models Not Filtered by Admin Ownership
**Location:** `backend/open_webui/utils/models.py:33-59` and `backend/open_webui/routers/openai.py:464-517`

**Code Flow:**
1. `get_all_base_models()` fetches models from:
   - OpenAI API (via `openai.get_all_models()`)
   - Ollama API (via `ollama.get_all_models()`)
   - Functions/Pipes (via `get_function_models()`)
2. These are combined and returned without filtering by admin ownership

**Problem:**
- OpenAI and Ollama models are fetched from external APIs and included for ALL users
- These should be filtered based on:
  - Which admin's API keys are configured (if using Portkey/multi-admin setup)
  - Group assignments (if models are assigned to specific groups)

**Impact:** Users see all OpenAI/Ollama models available via any admin's API configuration.

---

## Data Flow Analysis

### Current Flow (BROKEN):
```
1. User requests /api/models
2. main.py:get_models() calls get_all_models(request, user)
3. get_all_models() calls get_all_base_models()
4. get_all_base_models() calls:
   - openai.get_all_models() → Returns ALL OpenAI models
   - ollama.get_all_models() → Returns ALL Ollama models
   - get_function_models() → Returns ALL function models (BUG #1)
5. get_all_models() adds custom models from database (filtered correctly)
6. main.py:get_models() filters models for users:
   - Checks if model exists in database → Filters correctly
   - If model NOT in database → INCLUDES IT (BUG #2)
7. Returns all models to user
```

### Expected Flow (CORRECT):
```
1. User requests /api/models
2. main.py:get_models() calls get_all_models(request, user)
3. get_all_models() should filter at source:
   - Function models: Only from pipes assigned to user's groups OR created by user's admin
   - OpenAI models: Only from API keys assigned to user's groups OR user's admin
   - Ollama models: Only from Ollama instances assigned to user's groups OR user's admin
   - Custom models: Already filtered correctly
4. main.py:get_models() applies additional filtering:
   - For users: Only models they created OR assigned to their groups
   - For admins: Only models they created OR assigned to their groups
5. Returns filtered models
```

---

## Key Issues Summary

1. **Function/Pipe Models:** `(user.role == "user")` allows all users to see all pipes
2. **External Models:** Portkey/OpenAI models not in database are auto-included without access check
3. **Database Query:** `get_functions_by_type()` returns ALL functions without filtering
4. **Access Control:** Models may not have proper `access_control` set when created by admins
5. **API Models:** OpenAI/Ollama models not filtered by admin ownership or group assignment

---

## Additional Findings

### Model Creation Flow
**Location:** `backend/open_webui/routers/models.py:52-96`

**How Models Are Created:**
1. Admin creates a model via `/api/v1/models/create` endpoint
2. `ModelForm` includes optional `access_control` field
3. `access_control` can be:
   - `None`: Public access (available to all users with "user" role) - **THIS IS THE PROBLEM**
   - `{}`: Private access (restricted to owner only)
   - Custom dict: `{"read": {"group_ids": [...], "user_ids": [...]}, "write": {...}}`

**Problem:**
- If admin creates a model without setting `access_control` (or sets it to `None`), it becomes **public** to all users
- The comment in `backend/open_webui/models/models.py:84` says: `# - None: Public access, available to all users with the "user" role.`
- This means models created by Admin A without explicit `access_control` will be visible to users belonging to Admin B

**Root Cause:**
- Default behavior for `access_control=None` is to make models public
- Admins may not be aware they need to set `access_control` when creating models
- The UI may not be prompting admins to set group assignments when creating models

---

## Verification Steps Needed

1. **Check if models created by admins have `access_control` set with group assignments**
   - Query database: `SELECT id, created_by, access_control FROM model WHERE created_by LIKE '%@%'`
   - Verify if `access_control` is `None`, `{}`, or properly set with group_ids

2. **Check if `has_access()` function correctly identifies user's groups**
   - Test: Create a model with `access_control={"read": {"group_ids": ["group1"]}}`
   - Add user to `group1`
   - Verify user can see the model

3. **Check if `item_assigned_to_user_groups()` is being used for model filtering**
   - Currently used in `get_model_by_id()` but NOT in `get_all_models()` filtering
   - Should be used in `Models.get_all_models()` to check group assignments

4. **Verify the relationship between:**
   - Admin → Groups → Users
   - Admin → Models → Groups
   - User → Groups → Models (should be visible)

5. **Check UI behavior:**
   - When admin creates a model, does the UI prompt for group assignment?
   - Is `access_control` being set correctly from the UI?

---

## Files Requiring Investigation

1. `backend/open_webui/functions.py:149-221` - `get_function_models()`
2. `backend/open_webui/main.py:1155-1216` - `/api/models` endpoint
3. `backend/open_webui/utils/models.py:33-228` - `get_all_models()` and `get_all_base_models()`
4. `backend/open_webui/models/functions.py:156-171` - `get_functions_by_type()`
5. `backend/open_webui/models/models.py:179-192` - `get_all_models()` (database filtering)
6. `backend/open_webui/utils/access_control.py:118-137` - `has_access()` function
7. `backend/open_webui/utils/workspace_access.py:5-41` - `item_assigned_to_user_groups()`

