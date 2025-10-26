# Internal/Migrations Directory

This directory contains legacy Peewee ORM migration files used before Open WebUI transitioned to SQLAlchemy + Alembic. These files are maintained for backward compatibility to support upgrading from older Open WebUI versions. New migrations should be created using Alembic in the `migrations/` directory at the project root.

## Purpose

This directory provides:
- **Legacy Migration Support**: Handle database upgrades from Peewee-based versions
- **Backward Compatibility**: Enable smooth upgrades from old Open WebUI installations
- **Historical Record**: Document schema evolution during Peewee era
- **Transition Path**: Bridge from Peewee to SQLAlchemy/Alembic

## Migration Files (Chronological Order)

All migration files follow the pattern: `{number}_{description}.py`

### 001_initial_schema.py
**Purpose:** Initial database schema creation for Peewee ORM.

**Tables Created:**
- `user` - User accounts
- `auth` - Authentication credentials
- `chat` - Conversation records
- `message` (later renamed) - Chat messages
- `tag` - Tags for categorization
- `file` - File metadata
- `document` - Document references

**Historical Note:** This was the first schema when Open WebUI used Peewee exclusively.

### 002_add_local_sharing.py
**Purpose:** Add local chat sharing capability.

**Changes:**
- Add `share_id` column to `chat` table (UUID for public links)
- Enable generating shareable links for conversations

### 003_add_auth_api_key.py
**Purpose:** Add API key authentication support.

**Changes:**
- Add `api_key` column to `auth` table
- Enable programmatic API access via API keys

### 004_add_archived.py
**Purpose:** Add chat archiving feature.

**Changes:**
- Add `archived` boolean column to `chat` table
- Allow users to archive old conversations

### 005_add_updated_at.py
**Purpose:** Add updated_at timestamps to multiple tables.

**Changes:**
- Add `updated_at` column to `user`, `chat`, `auth`, `tag` tables
- Track when records were last modified

### 006_migrate_timestamps_and_charfields.py
**Purpose:** Normalize timestamp and string field types across database.

**Changes:**
- Standardize timestamp columns (consistent format)
- Migrate CharField to appropriate lengths
- Fix inconsistent field types

**Data Migration:** Yes (modifies existing data)

### 007_add_user_last_active_at.py
**Purpose:** Track user activity for session management.

**Changes:**
- Add `last_active_at` timestamp to `user` table
- Enable inactive user detection
- Support session timeout features

### 008_add_memory.py
**Purpose:** Add long-term memory feature for users.

**Tables Created:**
- `memory` - User memories (persistent context across chats)

**Columns:**
- `id` - Memory ID
- `user_id` - Owner
- `content` - Memory text
- `created_at`, `updated_at` - Timestamps

### 009_add_models.py
**Purpose:** Add model management system.

**Tables Created:**
- `model` - Model configurations and metadata

**Replaces:** Previous `modelfile` system

### 010_migrate_modelfiles_to_models.py
**Purpose:** Data migration from old modelfile system to new models table.

**Changes:**
- Copy data from `modelfile` table to `model` table
- Convert format to new schema
- Drop old `modelfile` table

**Data Migration:** Yes (complex data transformation)

### 011_add_user_settings.py
**Purpose:** Add per-user settings storage.

**Changes:**
- Add `settings` JSON column to `user` table
- Enable customizable user preferences

### 012_add_tools.py
**Purpose:** Add tool/function calling system.

**Tables Created:**
- `tool` - Custom tools for LLM function calling

**Columns:**
- `id` - Tool ID
- `name` - Tool name
- `content` - Tool code (Python)
- `meta` - Metadata (JSON)
- `valves` - Configuration (JSON)

### 013_add_user_info.py
**Purpose:** Expand user profile information.

**Changes:**
- Add `name` column to `user` table
- Add `profile_image_url` column
- Enable richer user profiles

### 014_add_files.py
**Purpose:** Enhance file management system.

**Changes:**
- Expand `file` table with additional columns
- Add `meta` JSON column for flexible metadata
- Add `hash` column for deduplication

### 015_add_functions.py
**Purpose:** Add functions system (separate from tools).

**Tables Created:**
- `function` - Custom Python functions

**Distinction:**
- **Tools**: User-facing, callable from chat
- **Functions**: Backend filters, middleware

### 016_add_valves_and_is_active.py
**Purpose:** Add configuration valves and activation flags.

**Changes:**
- Add `valves` JSON column to tools/functions
- Add `is_active` boolean for enable/disable
- Enable runtime configuration

### 017_add_user_oauth_sub.py
**Purpose:** Add OAuth subject identifier for OAuth login.

**Changes:**
- Add `oauth_sub` column to `user` table
- Link OAuth provider IDs to users
- Support Google/Microsoft/GitHub login

### 018_add_function_is_global.py
**Purpose:** Add global/per-user function scope.

**Changes:**
- Add `is_global` boolean to `function` table
- Differentiate global functions (all users) from user-specific

## Architecture & Patterns

### Peewee Migration Pattern
Unlike Alembic, Peewee migrations are simple Python scripts:

```python
def migrate(migrator, database):
    """Apply migration."""
    migrator.add_column('user', 'last_active_at', TimestampField(null=True))

def rollback(migrator, database):
    """Revert migration."""
    migrator.drop_column('user', 'last_active_at')
```

**Key Differences from Alembic:**
- No declarative schema (direct SQL operations)
- No automatic migration generation
- Manual up/down functions
- Simple, imperative style

### Migration Execution
Peewee migrations run via playhouse.migrate:

```python
from playhouse.migrate import PostgresqlMigrator, migrate

migrator = PostgresqlMigrator(database)

# Run migration
migrate(
    migrator.add_column('user', 'settings', JSONField(null=True))
)
```

## Integration Points

### internal/db.py → internal/migrations/
**Migration Execution:** Database initialization checks if Peewee migrations needed.

```python
# In internal/db.py
def init_db():
    # Check if database is Peewee-based (old version)
    if is_peewee_database():
        # Run legacy Peewee migrations
        run_peewee_migrations()

    # Then run Alembic migrations (current)
    run_alembic_migrations()
```

### internal/wrappers.py → internal/migrations/
**Compatibility Layer:** Wrappers provide Peewee-compatible interface for legacy code.

```python
# In internal/wrappers.py
class PeeweeCompatibilityWrapper:
    """Wrap SQLAlchemy to look like Peewee for legacy migrations."""
    pass
```

## Key Workflows

### Upgrading from Old Version
```
1. User runs new Open WebUI version
2. App startup detects old database (Peewee schema)
3. Check which Peewee migrations already applied
4. Run pending Peewee migrations (001-018)
5. Create Alembic migration table
6. Mark current state in Alembic
7. Future migrations use Alembic
```

### Migration Version Tracking
```
1. Peewee migrations tracked in `migratehistory` table
2. Each migration records:
   - Migration name
   - Applied timestamp
3. On startup, check which migrations not in history
4. Run pending migrations in order
```

## Important Notes

### Critical Information
- **Deprecated System**: Peewee migrations no longer used for new changes
- **Backward Compatibility Only**: Maintained for upgrades from old versions
- **Do Not Modify**: Never edit existing Peewee migration files
- **New Migrations**: Always use Alembic (root `migrations/` directory)

### Transition to SQLAlchemy
**Timeline:**
1. **Before Migration (v0.1.x)**: Pure Peewee ORM
2. **During Transition (v0.2.x)**: Dual Peewee + SQLAlchemy
3. **After Migration (v0.3.x+)**: Pure SQLAlchemy + Alembic

**Current State:** Peewee code removed, but migration files kept for upgrades.

### Why Keep These Files?
**Reasons:**
- Users upgrading from v0.1.x need these migrations
- Removing would break upgrade path
- Historical documentation
- Low maintenance burden (never change)

**Future:** May be removed in v2.0 (major version bump).

### Migration Safety
- All migrations tested on PostgreSQL and SQLite
- Data migrations (006, 010) carefully preserve data
- Rollback functions provided (though rarely used in production)
- Backup recommended before major version upgrades

### Database Compatibility
- **PostgreSQL**: Full support
- **SQLite**: Full support
- **MySQL**: Not tested (Open WebUI doesn't officially support MySQL)

### Testing Legacy Migrations
Not typically tested in CI/CD:
- Complex to set up old database versions
- Manual testing during major upgrades
- Upgrade path tested by community

### Troubleshooting Migration Issues
If migration fails:
1. Check database backup exists
2. Review migration log (find which migration failed)
3. Check database state manually (SQL query)
4. If 010_migrate_modelfiles_to_models fails:
   - This is the most complex migration
   - May need manual intervention
5. Contact community support with error details

### Future Deprecation
**Plan:**
- Mark as deprecated in v1.5
- Remove in v2.0 (require users on v1.x to upgrade via v1.5 first)
- Document upgrade path clearly

### For Developers
**Guidelines:**
- Never create new files in this directory
- Never modify existing files (even to fix bugs)
- All new migrations → Alembic
- If bug in legacy migration → document workaround, don't patch

### Documentation Purpose
This CLAUDE.md file serves as:
- Historical record of Peewee era
- Upgrade path documentation
- Warning to developers (don't use for new migrations)
- Maintenance notes for future
