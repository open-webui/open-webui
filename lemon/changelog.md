# Changelog

All notable changes to the Open WebUI group synchronization feature will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-08-06

#### Secure Group Feature
- Introduced secure groups with `secureGroup_` prefix that have special protection during SQL synchronization
- Added `SECURE_GROUP_PREFIX` constant in `group_sync_service.py`
- Added `is_secure_group()` helper function to identify secure groups
- Implemented filtering logic to prevent removal of users from secure groups during SQL sync
- Added comprehensive logging for secure group operations

#### Changes Made
1. **group_sync_service.py**:
   - Added secure group constants and helper function (lines 17-33)
   - Modified `synchronize_user_groups_from_sql()` to filter secure groups from removal (lines 379-393)
   - Updated summary logging to report number of preserved secure groups (lines 420-422)

2. **GroupPRD.md**:
   - Added secure group concept explanation (lines 167-170)
   - Added detailed secure group specification section (lines 173-186)
   - Updated synchronization logic documentation to include secure group handling (lines 225-232)
   - Added implementation details and code samples (lines 342-362)

3. **todo.md**:
   - Created comprehensive implementation plan for secure group feature
   - Included test scenarios and considerations

### Security Implications
- Secure groups provide protection against accidental removal of critical permissions
- Only manual admin intervention can remove users from secure groups
- SQL Server can still add users to secure groups, maintaining flexibility

### Testing Recommendations
1. Test user preservation in secure groups when not in SQL results
2. Test user addition to secure groups via SQL sync
3. Test mixed scenarios with both regular and secure groups
4. Verify logging accurately reflects secure group operations

### Test Implementation
- Created `test_secure_groups.py` with comprehensive test cases including:
  - Unit tests for `is_secure_group()` function
  - Integration test scenarios for synchronization logic
  - Logging verification tests
  - Manual test scenarios for development testing

### Notes
- Secure groups follow one-way synchronization pattern
- Error handling ensures sync failures don't disrupt authentication flow
- Feature is backward compatible with existing group synchronization
- **Important**: Actual tests have not been executed yet - they need to be run in the proper test environment