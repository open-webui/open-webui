# Model Visibility Bug - Solution Proposal

## Constraints
- ❌ **NO database schema changes** (no migrations, no new columns)
- ✅ **Backwards compatible** with existing code
- ✅ **Follow existing function signatures**
- ✅ **Optimized and scalable** (caching, batch operations)
- ✅ **Code/API-level solutions only**

## Solution Strategy Overview

### Core Principle
Use **existing database fields** (`access_control`, `created_by`, `user_id`) and **group relationships** to filter models at the API/code level, without requiring schema changes.

---

## Solution 1: Fix Function/Pipe Model Filtering

### Problem
`get_function_models()` allows all users to see all pipes via `(user.role == "user")` condition.

### Proposed Solution

**Location:** `backend/open_webui/functions.py:149-221`

**Approach:**
1. **For Users:** Only show pipes where:
   - Pipe creator's admin has assigned models to user's groups, OR
   - User's groups match pipe creator's groups (via group ownership), OR
   - Pipe has `access_control` set with user's group_ids

2. **For Admins:** Only show pipes they created

**Implementation Logic:**
```python
async def get_function_models(request, user: UserModel = None):
    if user is None:
        return []
    
    pipes = Functions.get_functions_by_type("pipe", active_only=True)
    pipe_models = []
    
    for pipe in pipes:
        # For admins: only their own pipes
        if user.role == "admin":
            if pipe.created_by != user.email:
                continue  # Skip pipes created by other admins
        
        # For users: check group assignments
        elif user.role == "user":
            # Get user's groups
            user_groups = Groups.get_groups_by_member_id(user.id)
            user_group_ids = [g.id for g in user_groups]
            
            # Get pipe creator (admin)
            pipe_creator = Users.get_user_by_email(pipe.created_by)
            if not pipe_creator:
                continue  # Skip if creator not found
            
            # Check if pipe creator has models assigned to user's groups
            has_access = False
            
            # Option 1: Check if pipe creator has any models assigned to user's groups
            creator_models = Models.get_all_models(pipe_creator.id, pipe_creator.email)
            for model in creator_models:
                if model.access_control:
                    read_groups = model.access_control.get("read", {}).get("group_ids", [])
                    if any(gid in user_group_ids for gid in read_groups):
                        has_access = True
                        break
            
            # Option 2: Check if user's admin (group owner) matches pipe creator
            # Get groups owned by user's admin
            user_admin = Users.get_user_by_id(user.id)  # Get user's admin via primary group
            # ... check if pipe creator is user's admin ...
            
            if not has_access:
                continue  # Skip this pipe
        
        # Process pipe and add to pipe_models...
```

**Optimization:**
- Cache user's groups (already done via `Groups.get_groups_by_member_id()`)
- Batch fetch all creator models once, then check group assignments
- Use `item_assigned_to_user_groups()` helper if available

---

## Solution 2: Filter External Models (Portkey/OpenAI)

### Problem
External models not in database are auto-included without access checks.

### Proposed Solution

**Location:** `backend/open_webui/main.py:1183-1188` and `backend/open_webui/utils/models.py:33-59`

**Approach:**
1. **Track API Key Ownership:** Determine which admin's API keys are being used
2. **Filter by Group Assignment:** Only include external models if:
   - The admin who owns the API key has models assigned to user's groups, OR
   - The external model ID matches a custom model in database with proper access_control

**Implementation Logic:**

**Step 1: Track API Key Ownership**
```python
# In get_all_models_responses() or similar
# Map API key index to admin email/user_id
# This can be done via:
# - Check which admin configured the API key (if stored in config)
# - Check if API key is in user-scoped config (RAG_OPENAI_API_KEY.get(email))
# - Default: if no owner, don't show to users (only admins)
```

**Step 2: Filter External Models**
```python
# In main.py:get_filtered_models()
else:
    # Model not in database (e.g., Portkey/external models)
    # Check if user should have access based on API key ownership
    
    # Get which admin's API key this model comes from
    api_key_owner = get_api_key_owner_for_model(model, request)
    
    if api_key_owner:
        # Check if api_key_owner has models assigned to user's groups
        user_groups = Groups.get_groups_by_member_id(user.id)
        user_group_ids = [g.id for g in user_groups]
        
        # Check if api_key_owner has any models with group assignments
        owner_models = Models.get_all_models(api_key_owner.id, api_key_owner.email)
        has_group_access = False
        for owner_model in owner_models:
            if owner_model.access_control:
                read_groups = owner_model.access_control.get("read", {}).get("group_ids", [])
                if any(gid in user_group_ids for gid in read_groups):
                    has_group_access = True
                    break
        
        if not has_group_access:
            continue  # Skip this external model
    
    # If no API key owner found, only show to admins
    if user.role == "user":
        continue  # Don't show external models to users if no owner
    
    filtered_models.append(model)
```

**Helper Function:**
```python
def get_api_key_owner_for_model(model: dict, request: Request) -> Optional[UserModel]:
    """
    Determine which admin's API key configuration this model comes from.
    
    Logic:
    1. Check model's urlIdx to identify which OPENAI_API_BASE_URLS index
    2. Check if that API key is in user-scoped config (RAG_OPENAI_API_KEY)
    3. Return the admin user who owns that API key
    """
    # Implementation details...
```

---

## Solution 3: Change Default Access Control Behavior

### Problem
Models with `access_control=None` default to public (visible to all users).

### Proposed Solution

**Location:** `backend/open_webui/models/models.py:179-192` and `backend/open_webui/utils/access_control.py:118-137`

**Approach:**
Change the default behavior so `access_control=None` means **private** (owner only), not public.

**Implementation Logic:**

**Option A: Change `has_access()` behavior**
```python
def has_access(
    user_id: str,
    type: str = "write",
    access_control: Optional[dict] = None,
) -> bool:
    # If access_control is None, treat as PRIVATE (owner only)
    # Only return True if user_id matches the item's user_id
    if access_control is None:
        # This should be checked at the caller level (user_id == item.user_id)
        # So return False here to force caller to check ownership
        return False
    
    # Existing logic for access_control dict...
```

**Option B: Change filtering logic in `get_all_models()`** ⭐ **RECOMMENDED**
```python
def get_all_models(
    self, user_id, user_email: str = None, permission: str = "read"
) -> list[ModelModel]:
    from open_webui.utils.workspace_access import item_assigned_to_user_groups
    
    with get_db() as db:
        raw_models = db.query(Model).all()

    filtered = []
    for model in raw_models:
        # If user is the creator, always include
        if model.created_by == user_email:
            filtered.append(model)
            continue
        
        # ENFORCE: If access_control is None, treat as PRIVATE (skip for other users)
        # This is the DEFAULT behavior - models are PRIVATE by default, NOT public
        if model.access_control is None:
            continue  # Skip models without access_control (private to creator only)
        
        # Check group assignments (NEW - Solution 4)
        if item_assigned_to_user_groups(user_id, model, permission):
            filtered.append(model)
            continue
        
        # Check has_access for models with explicit access_control
        if has_access(user_id, permission, model.access_control):
            filtered.append(model)

    return [ModelModel.model_validate(m) for m in filtered]
```

**Recommendation:** Use **Option B** (change filtering logic) because:
- ✅ **ENFORCES DEFAULT PRIVATE BEHAVIOR:** `access_control=None` = private (creator only)
- ✅ More explicit and easier to understand
- ✅ Doesn't change `has_access()` behavior (which might be used elsewhere)
- ✅ Backwards compatible (existing models with `access_control={}` still work)
- ✅ Includes group assignment check (Solution 4)

---

## Solution 4: Add Group Assignment Check to Model Filtering

### Problem
`item_assigned_to_user_groups()` is not used in `get_all_models()` filtering.

### Proposed Solution

**Location:** `backend/open_webui/models/models.py:179-192`

**Implementation:**
```python
def get_all_models(
    self, user_id, user_email: str = None, permission: str = "read"
) -> list[ModelModel]:
    from open_webui.utils.workspace_access import item_assigned_to_user_groups
    
    with get_db() as db:
        raw_models = db.query(Model).all()

    filtered = []
    for model in raw_models:
        # If user is the creator, always include
        if model.created_by == user_email:
            filtered.append(model)
            continue
        
        # Check group assignments (NEW)
        if item_assigned_to_user_groups(user_id, model, permission):
            filtered.append(model)
            continue
        
        # Check has_access (existing logic)
        if has_access(user_id, permission, model.access_control):
            filtered.append(model)

    return [ModelModel.model_validate(m) for m in filtered]
```

---

## Solution 5: Optimize with Caching and Batch Operations

### Problem
Multiple database queries and group checks can be slow.

### Proposed Solutions

**1. Cache User Groups**
```python
# Already implemented via Groups.get_groups_by_member_id()
# But can add request-level caching:
@lru_cache(maxsize=128)
def get_user_groups_cached(user_id: str) -> list[str]:
    groups = Groups.get_groups_by_member_id(user_id)
    return [g.id for g in groups]
```

**2. Batch Fetch Models**
```python
# Instead of fetching models one by one, batch fetch:
def get_models_by_creator_emails(creator_emails: list[str]) -> dict[str, list[ModelModel]]:
    """Batch fetch all models grouped by creator email"""
    with get_db() as db:
        models = db.query(Model).filter(Model.created_by.in_(creator_emails)).all()
    
    grouped = {}
    for model in models:
        if model.created_by not in grouped:
            grouped[model.created_by] = []
        grouped[model.created_by].append(ModelModel.model_validate(model))
    
    return grouped
```

**3. Pre-compute Group Access Map**
```python
def build_group_access_map(user_id: str, models: list[ModelModel]) -> dict[str, bool]:
    """Pre-compute which models user has access to via groups"""
    user_groups = Groups.get_groups_by_member_id(user_id)
    user_group_ids = [g.id for g in user_groups]
    
    access_map = {}
    for model in models:
        if model.access_control:
            read_groups = model.access_control.get("read", {}).get("group_ids", [])
            access_map[model.id] = any(gid in user_group_ids for gid in read_groups)
        else:
            access_map[model.id] = False
    
    return access_map
```

---

## Solution Architecture

### High-Level Flow

```
1. User requests /api/models
2. get_models() calls get_all_models(request, user)
3. get_all_models() calls get_all_base_models():
   a. openai.get_all_models() → Filter by API key ownership
   b. ollama.get_all_models() → Filter by admin ownership
   c. get_function_models() → Filter by group assignments
4. get_all_models() adds custom models (already filtered correctly)
5. main.py:get_models() applies final filtering:
   - For users: Only models they created OR assigned to their groups
   - For admins: Only models they created OR assigned to their groups
6. Return filtered models
```

### Key Helper Functions Needed

1. **`get_api_key_owner_for_model(model, request)`**
   - Determines which admin's API key a model comes from
   - Returns admin UserModel or None

2. **`user_has_access_to_admin_models(user, admin_email)`**
   - Checks if user's groups have access to any models created by admin
   - Returns bool

3. **`get_user_admin(user)`**
   - Gets the admin who owns the user's primary group
   - Returns admin UserModel or None

4. **`filter_models_by_group_access(models, user)`**
   - Batch filters models based on group assignments
   - Returns filtered list

---

## Implementation Priority

### Phase 1: Critical Fixes (FOCUS - Only Phase Needed)
**Note:** Since we ONLY use Portkey models created via Pipes, Phase 2 (external model filtering) is NOT needed.

1. ✅ **Fix `get_function_models()` filtering** (Solution 1) - **CRITICAL**
   - Users should only see pipes where their groups have access
   - Admins should only see pipes they created

2. ✅ **Change default `access_control=None` behavior** (Solution 3) - **CRITICAL**
   - **ENFORCE:** `access_control=None` = PRIVATE (creator only), NOT public
   - This is the default behavior that must be enforced

3. ✅ **Add group assignment check to `get_all_models()`** (Solution 4) - **CRITICAL**
   - Use `item_assigned_to_user_groups()` to check group access

### Phase 2: External Model Filtering (NOT NEEDED)
**Skipped:** We only use Portkey/Pipe models, not direct OpenAI/Ollama models.

### Phase 3: Optimization (DEFERRED)
**Deferred:** Caching and batch operations can be added later if performance issues arise.

---

## Backwards Compatibility Considerations

1. **Existing Models with `access_control=None`:**
   - **Before:** Visible to all users
   - **After:** Visible only to creator
   - **Impact:** Some users may lose access to models
   - **Mitigation:** Admins should update models to set `access_control` with group assignments

2. **Existing Function/Pipe Models:**
   - **Before:** Visible to all users
   - **After:** Visible only if assigned to user's groups
   - **Impact:** Users may lose access to some pipe models
   - **Mitigation:** Admins should assign pipe models to appropriate groups

3. **External Models:**
   - **Before:** Visible to all users
   - **After:** Visible only if admin's models are assigned to user's groups
   - **Impact:** Users may lose access to external models
   - **Mitigation:** Admins should create custom models with group assignments for external models they want to share

---

## Testing Strategy

1. **Unit Tests:**
   - Test `get_function_models()` with different user roles
   - Test `get_all_models()` with `access_control=None` vs `access_control={}`
   - Test group assignment filtering

2. **Integration Tests:**
   - Test complete flow: Admin creates model → Assigns to group → User in group sees it
   - Test: Admin A creates model → User in Admin B's group doesn't see it
   - Test: External models filtered correctly

3. **Performance Tests:**
   - Test with 100+ models, 10+ groups, 50+ users
   - Verify caching works correctly
   - Verify batch operations reduce DB queries

---

## Open Questions

1. **How to determine API key ownership?**
   - Is there a way to track which admin configured which API key?
   - Should we use user-scoped config (`RAG_OPENAI_API_KEY.get(email)`)?
   - What if multiple admins use the same API key?

2. **What about global/shared models?**
   - Should there be a way to mark models as "global" (visible to all)?
   - Or should all models require explicit group assignment?

3. **Migration path for existing models?**
   - Should we provide a script to update `access_control=None` models?
   - Or let admins manually update them?

4. **Performance impact?**
   - How many models/groups/users are we dealing with?
   - Will the additional group checks cause performance issues?
   - Should we add database indexes (but we said no schema changes...)?

---

## Recommendation

**Implement Phase 1 fixes ONLY (all we need):**
1. **Fix `get_function_models()` filtering logic** - Users only see pipes assigned to their groups
2. **ENFORCE default `access_control=None` = PRIVATE** - Creator only, NOT public
3. **Add group assignment check to `get_all_models()`** - Use `item_assigned_to_user_groups()`

**Key Enforcement:**
- **DEFAULT BEHAVIOR:** When a model is created without `access_control`, it MUST be PRIVATE (visible only to creator)
- **NO PUBLIC MODELS BY DEFAULT:** Models are never public unless explicitly set via `access_control` with group assignments
- **BACKWARDS COMPATIBLE:** Existing models with `access_control={}` (empty dict) remain private to creator

These three changes will fix the core issue. Since we only use Portkey/Pipe models, Phase 2 is not needed.

