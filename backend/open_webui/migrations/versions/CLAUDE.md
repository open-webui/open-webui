# Migrations/Versions Directory

This directory contains all individual Alembic migration files representing the chronological evolution of Open WebUI's database schema. Each file represents a single schema change (or set of related changes) that can be applied forward (upgrade) or reverted backward (downgrade).

## Purpose

This directory provides:
- **Historical Record**: Complete history of schema changes from initial creation to current state
- **Incremental Updates**: Each file applies one logical set of changes
- **Version Chain**: Files linked via `down_revision` forming a migration path
- **Rollback Support**: Each migration includes downgrade logic

## Migration Chain Overview

The migrations form a linked list from initial schema to current state:

```
7e5b5dc7342b_init.py (Initial schema)
  ↓
242a2047eae0_update_chat_table.py
  ↓
3781e22d8b01_update_message_table.py
  ↓
c69f45358db4_add_folder_table.py
  ↓
4ace53fd72c8_update_folder_table_datetime.py
  ↓
d31026856c01_update_folder_table_data.py
  ↓
1af9b942657b_migrate_tags.py
  ↓
3ab32c4b8f59_update_tags.py
  ↓
6a39f3d8e55c_add_knowledge_table.py
  ↓
c29facfe716b_update_file_table_path.py
  ↓
7826ab40b532_update_file_table.py
  ↓
c0fbf31ca0db_update_file_table.py
  ↓
922e7a387820_add_group_table.py
  ↓
ca81bd47c050_add_config_table.py
  ↓
af906e964978_add_feedback_table.py
  ↓
57c599a3cb57_add_channel_table.py
  ↓
9f0c9cd09105_add_note_table.py
  ↓
10vr9xyets5m_add_token_usage_tables.py
  ↓
3ff60f68c4f4_add_last_reset_date_to_token_usage.py
  ↓
e223b100ad81_add_reset_scheduling_to_token_groups.py (HEAD)
```

## Key Migrations

### 7e5b5dc7342b_init.py
**Purpose:** Initial database schema creation

**Tables Created:**
- `user` - User accounts
- `auth` - Authentication credentials
- `chat` - Conversation records
- `message` - Chat messages
- `file` - Uploaded files metadata
- `tool` - Custom tools
- `function` - Custom functions
- `model` - Model configurations
- `prompt` - Prompt templates
- `memory` - Long-term user memories

**Initial Schema:** Foundation for all future migrations

**Used by:** All subsequent migrations (base schema)

### 242a2047eae0_update_chat_table.py
**Purpose:** Enhance chat table with additional metadata

**Changes:**
- Add `title` column for chat names
- Add `pinned` column for starred chats
- Add `archived` column for archived chats
- Add `share_id` column for public sharing

**Enables:** Chat organization and sharing features

### 3781e22d8b01_update_message_table.py
**Purpose:** Extend message table for rich content

**Changes:**
- Add `images` JSON column for message attachments
- Add `files` JSON column for file references
- Add `citations` JSON column for source citations

**Enables:** Multimodal messages and RAG source tracking

### c69f45358db4_add_folder_table.py
**Purpose:** Add folder organization for chats

**Tables Created:**
- `folder` - Folder structure for organizing chats

**Columns:**
- `id` - Folder ID (UUID)
- `user_id` - Owner
- `name` - Folder name
- `parent_id` - Parent folder (for nested folders)
- `created_at`, `updated_at` - Timestamps

**Enables:** Hierarchical chat organization

### 4ace53fd72c8_update_folder_table_datetime.py
**Purpose:** Fix datetime column types in folder table

**Changes:**
- Convert timestamp columns to proper datetime types
- Ensure timezone-aware timestamps

**Fixes:** Database compatibility issues

### d31026856c01_update_folder_table_data.py
**Purpose:** Data migration for folder relationships

**Changes:**
- Migrate existing chat → folder relationships
- Update foreign key constraints

**Type:** Data migration (schema + data)

### 1af9b942657b_migrate_tags.py
**Purpose:** Introduce tagging system for chats

**Tables Created:**
- `tag` - Tag definitions
- `chat_tag` - Many-to-many relationship (chat ↔ tag)

**Enables:** Chat categorization and filtering

### 3ab32c4b8f59_update_tags.py
**Purpose:** Enhance tag system with metadata

**Changes:**
- Add `color` column to tags
- Add `icon` column for visual representation
- Add `user_id` for per-user tags

**Enables:** Personalized tag customization

### 6a39f3d8e55c_add_knowledge_table.py
**Purpose:** Add knowledge base management

**Tables Created:**
- `knowledge` - Knowledge base definitions

**Columns:**
- `id` - Knowledge ID
- `user_id` - Owner
- `name` - Knowledge base name
- `description` - Description
- `files` - JSON array of file IDs
- `created_at`, `updated_at` - Timestamps

**Enables:** RAG knowledge base organization

**Used by:**
- `routers/knowledge.py` - Knowledge CRUD
- `routers/retrieval.py` - Collection queries

### c29facfe716b_update_file_table_path.py
**Purpose:** Migrate file paths for cloud storage support

**Changes:**
- Update `path` column to support various storage providers
- Convert local paths to URI format (s3://, gs://, etc.)

**Enables:** Multi-provider storage abstraction

### 7826ab40b532_update_file_table.py
**Purpose:** Add file metadata columns

**Changes:**
- Add `size` column (file size in bytes)
- Add `mime_type` column
- Add `hash` column (SHA-256) for deduplication

**Enables:** File management and deduplication

### c0fbf31ca0db_update_file_table.py
**Purpose:** Additional file table enhancements

**Changes:**
- Add `processed` column (RAG processing status)
- Add `error` column (processing error messages)

**Enables:** RAG pipeline status tracking

### 922e7a387820_add_group_table.py
**Purpose:** Add user groups for permission management

**Tables Created:**
- `group` - User groups
- `group_member` - Group membership (user ↔ group)

**Enables:** Team collaboration and access control

### ca81bd47c050_add_config_table.py
**Purpose:** Add system configuration storage

**Tables Created:**
- `config` - Key-value configuration store

**Columns:**
- `key` - Configuration key (primary key)
- `value` - JSON value
- `updated_at` - Last modification time

**Enables:** Dynamic configuration without code changes

**Used by:**
- `routers/auths.py` - System configuration endpoints

### af906e964978_add_feedback_table.py
**Purpose:** Add user feedback collection

**Tables Created:**
- `feedback` - User feedback on chat responses

**Columns:**
- `id` - Feedback ID
- `user_id` - User who provided feedback
- `message_id` - Message being rated
- `rating` - Thumbs up/down
- `comment` - Optional text feedback
- `created_at` - Timestamp

**Enables:** Response quality tracking

### 57c599a3cb57_add_channel_table.py
**Purpose:** Add collaborative channels

**Tables Created:**
- `channel` - Shared conversation channels
- `channel_member` - Channel membership

**Enables:** Multi-user collaborative conversations

**Used by:**
- `routers/channels.py` - Channel CRUD
- `socket/main.py` - Real-time channel updates

### 9f0c9cd09105_add_note_table.py
**Purpose:** Add note-taking functionality

**Tables Created:**
- `note` - User notes

**Columns:**
- `id` - Note ID
- `user_id` - Owner
- `title` - Note title
- `content` - Markdown content
- `created_at`, `updated_at` - Timestamps

**Enables:** Note management alongside chats

### 10vr9xyets5m_add_token_usage_tables.py
**Purpose:** Add token usage tracking

**Tables Created:**
- `token_group` - Token usage groups (e.g., per-user, per-team)
- `token_usage` - Token consumption records

**Columns (token_group):**
- `name` - Group name (primary key)
- `models` - JSON array of model IDs to track
- `limit` - Token limit (BigInt)
- `created_at`, `updated_at` - Timestamps

**Columns (token_usage):**
- `group_name` - Group reference (primary key)
- `token_in` - Input tokens consumed
- `token_out` - Output tokens consumed
- `token_total` - Total tokens
- `updated_at` - Last update

**Enables:** Token budget enforcement and billing

**Used by:**
- `socket/main.py` - Real-time token tracking
- `utils/middleware.py` - Token limit checks

### 3ff60f68c4f4_add_last_reset_date_to_token_usage.py
**Purpose:** Add reset tracking for token limits

**Changes:**
- Add `last_reset_date` column to `token_usage`

**Enables:** Monthly/weekly token limit resets

### e223b100ad81_add_reset_scheduling_to_token_groups.py
**Purpose:** Add configurable reset schedules

**Changes:**
- Add `reset_schedule` column to `token_group` (JSON)
- Supports cron-like scheduling

**Enables:** Flexible token limit reset policies (daily, weekly, monthly, custom)

## Migration File Structure

Each migration file follows this pattern:

```python
"""Description of changes

Revision ID: 10vr9xyets5m
Revises: d31026856c01
Create Date: 2025-08-08 04:21:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '10vr9xyets5m'  # This migration's ID
down_revision = 'd31026856c01'  # Previous migration
branch_labels = None
depends_on = None

def upgrade():
    """Apply schema changes"""
    op.create_table('new_table', ...)
    op.add_column('existing_table', ...)

def downgrade():
    """Revert schema changes"""
    op.drop_table('new_table')
    op.drop_column('existing_table', ...)
```

## Common Migration Operations

### Creating Tables
```python
op.create_table(
    'table_name',
    sa.Column('id', sa.String(), primary_key=True),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.BigInteger(), nullable=True),
)
```

### Adding Columns
```python
op.add_column('table_name', sa.Column('new_column', sa.Text()))
```

### Dropping Columns
```python
op.drop_column('table_name', 'old_column')
```

### Renaming Columns
```python
op.alter_column('table_name', 'old_name', new_column_name='new_name')
```

### Creating Indexes
```python
op.create_index('idx_user_email', 'user', ['email'])
```

### Data Migrations
```python
def upgrade():
    # Schema change
    op.add_column('user', sa.Column('status', sa.String(20)))

    # Data migration
    connection = op.get_bind()
    connection.execute(
        "UPDATE user SET status = 'active' WHERE verified = true"
    )
```

## Integration Points

### models/* → versions/
ORM models define tables, migrations create them:
```
models/chats.py defines Chat model
  ↓
242a2047eae0_update_chat_table.py creates chat table
```

### alembic CLI → versions/
Alembic applies migrations in order:
```bash
alembic upgrade head
  ↓
Reads down_revision chain
  ↓
Applies pending migrations from versions/
```

### internal/db.py → versions/
Database initialization applies migrations:
```python
def init_db():
    from alembic import command
    command.upgrade(alembic_cfg, "head")
```

## Important Notes

### Critical Dependencies
- Each migration depends on previous migration via `down_revision`
- Migrations must be applied in order (chain cannot be broken)
- Missing migrations cause `alembic upgrade` to fail

### Naming Convention
Files named: `{revision_id}_{description}.py`
- Revision ID generated by Alembic (hash-based)
- Description from `-m` argument to `alembic revision`

### Never Edit Applied Migrations
Once a migration is applied to any database (especially production), never edit it. Instead:
1. Create new migration to fix issues
2. Use `alembic downgrade` if necessary

### Testing Migrations
Always test both upgrade() and downgrade():
```bash
alembic upgrade +1  # Apply one migration
alembic downgrade -1  # Rollback
```

### Data Migration Cautions
- Can be slow for large tables
- May require downtime
- Test on production-sized dataset first
- Consider batching for large updates

### Database-Specific Considerations
Some operations behave differently:
- **SQLite**: Limited ALTER TABLE (use batch mode)
- **PostgreSQL**: Full DDL support
- **MySQL**: Different transaction semantics

### Conflict Resolution
If two branches create migrations with same parent:
```bash
alembic merge <rev1> <rev2> -m "Merge migrations"
```

Creates merge migration that depends on both.
