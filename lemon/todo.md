# Secure Group Implementation TODO

## Overview
Implement secure group functionality where groups with the prefix "secureGroup_" cannot be removed from users during SQL synchronization, ensuring critical permissions are protected.

## Tasks

### 1. Update group_sync_service.py
- [x] Add SECURE_GROUP_PREFIX constant
- [x] Add is_secure_group() helper function
- [x] Modify synchronize_user_groups_from_sql() to filter secure groups from removal
- [x] Add appropriate logging for secure group handling

### 2. Code Changes Required

#### 2.1 Add Constants and Helper Function
```python
# Add at the top of group_sync_service.py after imports
SECURE_GROUP_PREFIX = "secureGroup_"

def is_secure_group(group_name: str) -> bool:
    """
    Check if a group is a secure group based on its name prefix.
    
    Args:
        group_name: The name of the group to check
        
    Returns:
        bool: True if the group is a secure group, False otherwise
    """
    return group_name.startswith(SECURE_GROUP_PREFIX) if group_name else False
```

#### 2.2 Modify Group Removal Logic
In the `synchronize_user_groups_from_sql()` function, update the group removal section:

```python
# Replace the existing groups_to_remove_ids calculation with:
groups_to_remove_ids_initial = current_ouw_group_ids_set - final_target_ouw_group_ids_set
groups_to_remove_ids = set()

# Filter out secure groups
for group_id_to_check in groups_to_remove_ids_initial:
    try:
        group = groups_table.get_group_by_id(group_id_to_check)
        if group and is_secure_group(group.name):
            log.info(f"Preserving user {user.email} membership in secure group '{group.name}' (ID: {group_id_to_check}) - secure groups cannot be removed via SQL sync")
        else:
            groups_to_remove_ids.add(group_id_to_check)
    except Exception as e:
        log.warning(f"Error checking group {group_id_to_check} for secure status: {str(e)}. Including in removal list.")
        groups_to_remove_ids.add(group_id_to_check)
```

### 3. Testing Scenarios ⚠️ (Not Yet Executed)

#### 3.1 Test Case 1: User in Secure Group Not Removed
1. Create a group named "secureGroup_Administrators"
2. Add a user to this group
3. Ensure SQL sync doesn't return this group
4. Verify user remains in the secure group after sync

#### 3.2 Test Case 2: User Added to Secure Group via SQL
1. Configure SQL to return "secureGroup_DataScientists"
2. Run sync for a user not in this group
3. Verify user is added to the secure group

#### 3.3 Test Case 3: Mixed Groups
1. User is in: ["GroupA", "secureGroup_Special", "GroupB"]
2. SQL returns: ["GroupA", "GroupC"]
3. Expected result: User should be in ["GroupA", "GroupC", "secureGroup_Special"]

### 4. Documentation Updates
- [x] GroupPRD.md already updated with secure group specifications
- [x] Add inline documentation in code
- [x] Update changelog.md

### 5. Considerations
- Secure groups provide one-way synchronization (can add, cannot remove)
- Only admins can manually remove users from secure groups via UI
- Logging is critical for audit trail of secure group operations
- Error handling should not break the sync process

## Implementation Order
1. Add constants and helper function ✅
2. Update synchronization logic ✅
3. Test implementation ❌ (Pending)
4. Update documentation and changelog ✅

## Status: PARTIALLY COMPLETED
Code implementation is complete, but testing has not been performed. The secure group feature code is ready but requires testing before production use.

## Testing Requirements
The following tests need to be executed to verify the secure group functionality:

### Unit Tests Needed:
1. Test `is_secure_group()` function with various inputs
2. Test the filtering logic in isolation

### Integration Tests Needed:
1. Full synchronization flow with secure groups
2. Error handling scenarios
3. Performance testing with multiple secure groups

### Manual Testing Steps:
1. Create test users and groups in Open WebUI
2. Set up test data in SQL Server
3. Execute synchronization and verify results
4. Check logs for proper secure group handling