# Phase 1 Implementation Plan - Model Visibility Fix

## Overview
Fix model visibility so users only see:
1. Models they created themselves
2. Models assigned to their groups by their admin
3. **NOT** models created by other admins
4. **NOT** models created by other users

## Key Enforcement
- **DEFAULT BEHAVIOR:** `access_control=None` = **PRIVATE** (creator only), **NOT public**
- Models are **NEVER public by default** - they must be explicitly shared via group assignments

---

## Implementation Tasks

### Task 1: Fix `get_function_models()` Filtering Logic

**File:** `backend/open_webui/functions.py`
**Location:** Lines 149-221
**Current Issue:** Line 158: `(user.role == "user")` allows ALL users to see ALL pipes

**Changes Needed:**

1. **For Admins:** Only show pipes they created
   ```python
   if user.role == "admin":
       if pipe.created_by != user.email:
           continue  # Skip pipes created by other admins
   ```

2. **For Users:** Only show pipes where:
   - Pipe creator has models assigned to user's groups, OR
   - User's groups match pipe creator's groups (via group ownership)
   
   **Logic:**
   ```python
   elif user.role == "user":
       # Get user's groups
       user_groups = Groups.get_groups_by_member_id(user.id)
       user_group_ids = [g.id for g in user_groups]
       
       # Get pipe creator (admin)
       pipe_creator = Users.get_user_by_email(pipe.created_by)
       if not pipe_creator:
           continue  # Skip if creator not found
       
       # Check if pipe creator has any models assigned to user's groups
       has_access = False
       creator_models = Models.get_all_models(pipe_creator.id, pipe_creator.email)
       for model in creator_models:
           if model.access_control:
               read_groups = model.access_control.get("read", {}).get("group_ids", [])
               if any(gid in user_group_ids for gid in read_groups):
                   has_access = True
                   break
       
       if not has_access:
           continue  # Skip this pipe
   ```

3. **For Super Admins:** Keep existing behavior (see all)

**Dependencies:**
- `Groups.get_groups_by_member_id()` - Already exists
- `Users.get_user_by_email()` - Already exists
- `Models.get_all_models()` - Already exists

---

### Task 2: Enforce Default Private Behavior for Models

**File:** `backend/open_webui/models/models.py`
**Location:** Lines 179-192 (`get_all_models()` method)

**Current Issue:** Models with `access_control=None` are treated as public (visible to all users)

**Changes Needed:**

1. **Change filtering logic to treat `access_control=None` as PRIVATE:**
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
           # DEFAULT BEHAVIOR: Models are PRIVATE by default, NOT public
           if model.access_control is None:
               continue  # Skip models without access_control (private to creator only)
           
           # Check group assignments (NEW)
           if item_assigned_to_user_groups(user_id, model, permission):
               filtered.append(model)
               continue
           
           # Check has_access for models with explicit access_control
           if has_access(user_id, permission, model.access_control):
               filtered.append(model)

       return [ModelModel.model_validate(m) for m in filtered]
   ```

**Key Changes:**
- ✅ Added `item_assigned_to_user_groups()` check (Task 3)
- ✅ `access_control=None` → Skip (private to creator)
- ✅ `access_control={}` → Check `has_access()` (empty dict = private, but check anyway)
- ✅ `access_control={"read": {...}}` → Check group assignments and `has_access()`

**Dependencies:**
- `item_assigned_to_user_groups()` - Already exists in `backend/open_webui/utils/workspace_access.py`

---

### Task 3: Add Group Assignment Check (Already Included in Task 2)

**File:** `backend/open_webui/models/models.py`
**Location:** Lines 179-192 (`get_all_models()` method)

**Status:** ✅ **Already included in Task 2** - The `item_assigned_to_user_groups()` check is added in the updated `get_all_models()` method.

**What it does:**
- Checks if model is assigned to any group the user is a member of
- Checks if user owns any group that has access to the model
- Works alongside `has_access()` for comprehensive filtering

---

## Additional Enforcement Points

### 1. Model Creation Endpoint
**File:** `backend/open_webui/routers/models.py`
**Location:** Lines 52-96 (`create_new_model()`)

**Verify:** When a model is created without `access_control`, it should default to `None` (which we now treat as private).

**Current Code:**
```python
model = Models.insert_new_model(form_data, creator_user_id, creator_email)
```

**Check:** `ModelForm.access_control` defaults to `None` - ✅ This is correct.

### 2. Model Update Endpoint
**File:** `backend/open_webui/routers/models.py`
**Location:** Lines 182-207 (`update_model_by_id()`)

**Verify:** When updating a model, if `access_control` is not provided, it should remain `None` (private).

**Current Code:** Uses `form_data.access_control` - ✅ Should be fine.

### 3. Main API Endpoint Filtering
**File:** `backend/open_webui/main.py`
**Location:** Lines 1155-1216 (`get_models()` endpoint)

**Verify:** The `get_filtered_models()` function should also respect the private default.

**Current Code:** Line 1183-1188 includes external models without database entry. Since we only use Portkey/Pipe models, this should be fine, but we should verify it doesn't bypass our filtering.

---

## Testing Checklist

### Test Case 1: Default Private Behavior
- [ ] Admin A creates a model without setting `access_control`
- [ ] Verify: Model is visible to Admin A only
- [ ] Verify: User in Admin A's group does NOT see the model
- [ ] Verify: Admin B does NOT see the model

### Test Case 2: Group Assignment
- [ ] Admin A creates a model with `access_control={"read": {"group_ids": ["group1"]}}`
- [ ] Add User to `group1`
- [ ] Verify: User can see the model
- [ ] Verify: User not in `group1` does NOT see the model

### Test Case 3: Pipe/Function Models
- [ ] Admin A creates a pipe/function
- [ ] Admin A creates a model using that pipe, assigns to `group1`
- [ ] User in `group1` should see the pipe model
- [ ] User not in `group1` should NOT see the pipe model
- [ ] Admin B should NOT see Admin A's pipe models

### Test Case 4: User-Created Models
- [ ] User creates a model (if allowed)
- [ ] Verify: User can see their own model
- [ ] Verify: Other users do NOT see the model
- [ ] Verify: Admin does NOT see the model (unless assigned to their group)

### Test Case 5: Backwards Compatibility
- [ ] Existing models with `access_control={}` (empty dict) should remain private
- [ ] Existing models with `access_control=None` should become private (if they were public before)
- [ ] Existing models with group assignments should continue to work

---

## Implementation Order

1. **Task 2 First** (Enforce default private behavior)
   - This is the foundation - ensures models are private by default
   - Includes Task 3 (group assignment check)

2. **Task 1 Second** (Fix pipe/function filtering)
   - Builds on Task 2's group assignment logic
   - Uses the same filtering principles

---

## Files to Modify

1. ✅ `backend/open_webui/functions.py` - Fix `get_function_models()`
2. ✅ `backend/open_webui/models/models.py` - Fix `get_all_models()`

**Total:** 2 files to modify

---

## Risk Assessment

### Low Risk
- ✅ No database schema changes
- ✅ Backwards compatible (existing models with `access_control={}` still work)
- ✅ Uses existing helper functions

### Medium Risk
- ⚠️ Some users may lose access to models that were previously public (if `access_control=None`)
- **Mitigation:** Admins should update models to set `access_control` with group assignments

### Testing Required
- ✅ Test all 5 test cases above
- ✅ Test with multiple admins, groups, and users
- ✅ Verify performance with large number of models

---

## Success Criteria

1. ✅ Users only see models assigned to their groups
2. ✅ Users only see models they created
3. ✅ Admins only see models they created (unless assigned to their groups)
4. ✅ Default behavior: `access_control=None` = PRIVATE (creator only)
5. ✅ Group assignments work correctly
6. ✅ Pipe/function models filtered correctly
7. ✅ Backwards compatible with existing models

