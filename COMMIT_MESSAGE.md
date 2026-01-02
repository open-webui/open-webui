Remove unused would_show_child column and fix migration idempotency

## Summary

Removed the unused `would_show_child` column from the `moderation_session` table.
The column existed in the database but was not defined in the SQLAlchemy model,
which could cause runtime errors. All code references have been removed and a
migration has been created to drop the column from the database.

Additionally, fixed multiple Alembic migration files to be idempotent by checking
for existence of tables, columns, and indexes before creating or dropping them.
This prevents migration errors when migrations are run multiple times or on
databases that already have some schema elements.

## Changes

### Primary: Remove would_show_child column

**Backend Changes:**
- `backend/open_webui/routers/moderation_scenarios.py`:
  - Removed `would_show_child` from `ModerationSessionPayload` class
  - Removed `would_show_child` parameter from `ModerationSessionForm` instantiation
  - Updated comments to document the removal

- `backend/open_webui/models/moderation.py`:
  - Updated deprecated comments to note that `would_show_child` has been removed
  - Changed comments from "Deprecated - no longer collected" to note migration reference
  - Added migration reference (84b2215f7772) in comments

**Frontend Changes:**
- `src/lib/apis/moderation/index.ts`:
  - Removed `would_show_child` from `ModerationSessionPayload` interface
  - Removed `would_show_child` from `ModerationSessionResponse` interface

- `src/routes/(app)/moderation-scenario/+page.svelte`:
  - Removed `would_show_child: undefined` from `saveModerationSession` calls
  - Updated documentation comments to reflect column removal
  - Clarified that Step 3 completion is determined by satisfaction check fields

**Database Migration:**
- `backend/open_webui/migrations/versions/84b2215f7772_remove_unused_would_show_child_column_.py`:
  - Created idempotent migration to drop `would_show_child` column
  - Checks for column existence before dropping
  - Includes proper downgrade function to restore column if needed

### Secondary: Migration idempotency fixes

Fixed multiple migration files to be idempotent by adding existence checks before
creating or dropping database objects. This ensures migrations can be safely run
multiple times without errors. Fixed migrations include:

- Table creation migrations (check if table exists)
- Column addition migrations (check if column exists)
- Index creation migrations (check if index exists)
- Column/table drop migrations (check before dropping)

## Impact

- **Database Schema**: `moderation_session` table now has 29 columns (down from 30),
  matching the SQLAlchemy model definition exactly
- **Code Cleanliness**: Removed all references to unused column, preventing potential
  runtime errors from schema mismatches
- **Migration Safety**: All migrations are now idempotent and can be safely re-run

## Verification

- Verified column was removed from database (29 columns remain)
- Verified all code references have been removed
- Verified migration file is properly documented
- Database schema now matches model definitions
