# Database Schema Reference

> **Generated:** 2026-02-03 from SQLAlchemy models
> **Source:** `backend/open_webui/models/`
> **Regenerate:** `python docs/scripts/generate_schema_docs.py`

---

## Prerequisites

- `DATA_MODEL.md` — Conceptual understanding of entity relationships

---

## Overview

| Table | Description | Primary Key |
|-------|-------------|-------------|
| `users` | User accounts | `id` (UUID) |
| `auths` | Authentication credentials | `id` (UUID, same as user_id) |
| `api_keys` | API access tokens | `id` (UUID) |
| `groups` | User groups | `id` (UUID) |
| `group_members` | Group membership | `id` (UUID) |
| `chats` | Conversation sessions | `id` (UUID) |
| `chat_messages` | Individual messages | `(chat_id, message_id)` |
| `channels` | Communication spaces | `id` (UUID) |
| `channel_members` | Channel membership | `id` (UUID) |
| `messages` | Channel messages | `id` (UUID) |
| `message_reactions` | Message reactions | `id` (UUID) |
| `channel_webhooks` | Incoming webhooks | `id` (UUID) |
| `files` | Uploaded files | `id` (UUID) |
| `knowledge` | Knowledge bases | `id` (UUID) |
| `knowledge_files` | Knowledge-file association | `id` (UUID) |
| `memories` | User memories | `id` (UUID) |
| `notes` | User notes | `id` (UUID) |
| `folders` | Chat organization | `id` (UUID) |
| `tags` | Chat tags | `id` (String) |
| `prompts` | Prompt templates | `id` (UUID) |
| `prompt_history` | Prompt versions | `id` (UUID) |
| `functions` | Custom functions | `id` (String) |
| `tools` | Tool definitions | `id` (String) |
| `models` | Model configurations | `id` (String) |
| `feedbacks` | User feedback | `id` (UUID) |
| `oauth_sessions` | OAuth token storage | `id` (UUID) |

---

## Table: users

User accounts and profiles.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `email` | String | No | — | Unique, indexed, login identifier |
| `name` | String | Yes | — | Display name |
| `role` | String | No | `'user'` | Authorization role (admin/user/pending) |
| `profile_image_url` | String | Yes | — | Avatar URL |
| `settings` | JSON | Yes | `{}` | User preferences |
| `info` | JSON | Yes | `{}` | Additional user info |
| `oauth_sub` | String | Yes | — | OAuth subject identifier |
| `last_active_at` | BigInteger | Yes | — | Last activity timestamp |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Indexes:**
- `ix_users_email` (unique)
- `ix_users_oauth_sub`
- `ix_users_created_at`

---

## Table: auths

Authentication credentials (1:1 with users).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key (same as user_id) |
| `email` | String | No | — | Login email |
| `password` | String | Yes | — | Hashed password (bcrypt/argon2) |
| `active` | Boolean | No | `True` | Account active status |

**Foreign Keys:**
- `id` → `users.id`

---

## Table: api_keys

API access tokens for programmatic access.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Owner reference |
| `name` | String | Yes | — | Key display name |
| `key` | String | No | — | Hashed key value |
| `expires_at` | BigInteger | Yes | — | Expiration timestamp |
| `last_used_at` | BigInteger | Yes | — | Last usage timestamp |
| `data` | JSON | Yes | `{}` | Additional metadata |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_api_keys_user_id`
- `ix_api_keys_key` (unique)

---

## Table: groups

User groups for access control.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Owner/creator |
| `name` | String | No | — | Group name |
| `description` | Text | Yes | — | Group description |
| `permissions` | JSON | Yes | `{}` | Permission definitions |
| `access_control` | JSON | Yes | — | Access rules |
| `meta` | JSON | Yes | `{}` | Additional metadata |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

---

## Table: group_members

Group membership associations.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `group_id` | String | No | — | Group reference |
| `user_id` | String | No | — | User reference |
| `created_at` | BigInteger | No | `now()` | Join timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `group_id` → `groups.id`
- `user_id` → `users.id`

**Indexes:**
- `ix_group_members_group_id`
- `ix_group_members_user_id`
- Unique constraint on `(group_id, user_id)`

---

## Table: chats

Conversation sessions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Owner reference |
| `title` | Text | Yes | — | Conversation title |
| `chat` | JSON | No | — | Message history (legacy structure) |
| `share_id` | String | Yes | — | Public sharing identifier |
| `archived` | Boolean | No | `False` | Archive flag |
| `pinned` | Boolean | Yes | `False` | Pin to top flag |
| `folder_id` | String | Yes | — | Organization folder |
| `meta` | JSON | Yes | `{}` | Metadata (tags, etc.) |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`
- `folder_id` → `folders.id`

**Indexes:**
- `ix_chats_user_id`
- `ix_chats_folder_id`
- `ix_chats_share_id` (unique)
- `ix_chats_updated_at`
- `ix_chats_created_at`

---

## Table: chat_messages

Individual messages for analytics (dual-write with chats.chat).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `chat_id` | String | No | — | Chat reference (composite PK) |
| `message_id` | String | No | — | Message ID (composite PK) |
| `user_id` | String | No | — | User who sent/received |
| `role` | String | No | — | `user`, `assistant`, `system` |
| `content` | Text/JSON | Yes | — | Message content |
| `output` | Text/JSON | Yes | — | Generated output (if different) |
| `model_id` | String | Yes | — | Model that generated response |
| `status_history` | JSON | Yes | — | Status transitions |
| `error` | JSON | Yes | — | Error details if failed |
| `usage` | JSON | Yes | — | Token usage metrics |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Primary Key:** `(chat_id, message_id)`

**Foreign Keys:**
- `chat_id` → `chats.id`
- `user_id` → `users.id`

**Indexes:**
- `ix_chat_messages_user_id`
- `ix_chat_messages_model_id`
- `ix_chat_messages_created_at`

---

## Table: channels

Communication spaces (group chat, DM).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Creator reference |
| `type` | String | Yes | — | `null`/`group` or `dm` |
| `name` | String | Yes | — | Channel name |
| `description` | Text | Yes | — | Channel description |
| `is_private` | Boolean | No | `False` | Visibility flag |
| `access_control` | JSON | Yes | — | Access rules |
| `meta` | JSON | Yes | `{}` | Additional metadata |
| `data` | JSON | Yes | `{}` | Channel-specific data |
| `archived_at` | BigInteger | Yes | — | Archive timestamp |
| `archived_by` | String | Yes | — | Who archived |
| `deleted_at` | BigInteger | Yes | — | Soft delete timestamp |
| `deleted_by` | String | Yes | — | Who deleted |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_channels_user_id`
- `ix_channels_type`
- `ix_channels_created_at`

---

## Table: channel_members

Channel membership with status tracking.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `channel_id` | String | No | — | Channel reference |
| `user_id` | String | No | — | User reference |
| `role` | String | Yes | `'member'` | Member role |
| `status` | String | Yes | `'joined'` | `joined`, `left`, `invited` |
| `is_active` | Boolean | No | `True` | Currently active |
| `is_channel_muted` | Boolean | No | `False` | Notifications muted |
| `is_channel_pinned` | Boolean | No | `False` | Pinned in sidebar |
| `last_read_at` | BigInteger | Yes | — | Last read timestamp |
| `invited_at` | BigInteger | Yes | — | Invitation timestamp |
| `created_at` | BigInteger | No | `now()` | Join timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `channel_id` → `channels.id`
- `user_id` → `users.id`

**Indexes:**
- `ix_channel_members_channel_id`
- `ix_channel_members_user_id`
- Unique constraint on `(channel_id, user_id)`

---

## Table: messages

Channel messages (distinct from chat messages).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Author reference |
| `channel_id` | String | No | — | Channel reference |
| `reply_to_id` | String | Yes | — | Reply to message ID |
| `parent_id` | String | Yes | — | Thread parent ID |
| `content` | Text | No | — | Message content |
| `is_pinned` | Boolean | No | `False` | Pinned message flag |
| `pinned_at` | BigInteger | Yes | — | Pin timestamp |
| `pinned_by` | String | Yes | — | Who pinned |
| `data` | JSON | Yes | `{}` | Additional data |
| `meta` | JSON | Yes | `{}` | Metadata |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`
- `channel_id` → `channels.id`
- `reply_to_id` → `messages.id`
- `parent_id` → `messages.id`

**Indexes:**
- `ix_messages_channel_id`
- `ix_messages_user_id`
- `ix_messages_created_at`

---

## Table: message_reactions

Emoji reactions on channel messages.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | User who reacted |
| `message_id` | String | No | — | Message reference |
| `name` | String | No | — | Emoji name/code |
| `created_at` | BigInteger | No | `now()` | Reaction timestamp |

**Foreign Keys:**
- `user_id` → `users.id`
- `message_id` → `messages.id`

**Indexes:**
- `ix_message_reactions_message_id`
- Unique constraint on `(user_id, message_id, name)`

---

## Table: files

Uploaded file references.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Uploader reference |
| `hash` | String | Yes | — | Content hash (deduplication) |
| `filename` | String | No | — | Original filename |
| `path` | String | No | — | Storage path |
| `data` | JSON | Yes | `{}` | Parsed content |
| `meta` | JSON | Yes | `{}` | File metadata |
| `access_control` | JSON | Yes | — | Access rules |
| `created_at` | BigInteger | No | `now()` | Upload timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_files_user_id`
- `ix_files_hash`

---

## Table: knowledge

Knowledge bases for RAG.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Owner reference |
| `name` | String | No | — | Knowledge base name |
| `description` | Text | Yes | — | Description |
| `access_control` | JSON | Yes | — | Access rules |
| `meta` | JSON | Yes | `{}` | Additional metadata |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_knowledge_user_id`

---

## Table: knowledge_files

Association between knowledge bases and files.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `knowledge_id` | String | No | — | Knowledge base reference |
| `file_id` | String | No | — | File reference |
| `user_id` | String | No | — | Who added the file |
| `created_at` | BigInteger | No | `now()` | Association timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `knowledge_id` → `knowledge.id`
- `file_id` → `files.id`
- `user_id` → `users.id`

**Indexes:**
- `ix_knowledge_files_knowledge_id`
- `ix_knowledge_files_file_id`

---

## Table: memories

User context memories.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | User reference |
| `content` | Text | No | — | Memory content |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_memories_user_id`

---

## Table: prompts

Reusable prompt templates.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | Creator reference |
| `command` | String | No | — | Trigger command (unique) |
| `name` | String | No | — | Display name |
| `content` | Text | No | — | Prompt template |
| `tags` | JSON | Yes | `[]` | Categorization tags |
| `access_control` | JSON | Yes | — | Access rules |
| `version_id` | String | Yes | — | Current version reference |
| `data` | JSON | Yes | `{}` | Additional data |
| `meta` | JSON | Yes | `{}` | Metadata |
| `is_active` | Boolean | No | `True` | Active flag |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_prompts_user_id`
- `ix_prompts_command` (unique)

---

## Table: prompt_history

Prompt version history.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `prompt_id` | String | No | — | Prompt reference |
| `parent_id` | String | Yes | — | Previous version |
| `snapshot` | JSON | No | — | Complete prompt state |
| `user_id` | String | No | — | Who made the change |
| `commit_message` | Text | Yes | — | Change description |
| `created_at` | BigInteger | No | `now()` | Version timestamp |

**Foreign Keys:**
- `prompt_id` → `prompts.id`
- `parent_id` → `prompt_history.id`
- `user_id` → `users.id`

**Indexes:**
- `ix_prompt_history_prompt_id`

---

## Table: functions

Custom Python functions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String | No | — | Primary key (unique ID) |
| `user_id` | String | No | — | Creator reference |
| `name` | String | No | — | Display name |
| `type` | String | No | — | `filter` or `action` |
| `content` | Text | No | — | Python source code |
| `meta` | JSON | Yes | `{}` | Description, manifest |
| `valves` | JSON | Yes | `{}` | Configuration parameters |
| `is_active` | Boolean | No | `True` | Enabled flag |
| `is_global` | Boolean | No | `False` | Applies to all users |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_functions_user_id`
- `ix_functions_type`

---

## Table: tools

Tool definitions (OpenAPI specs).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String | No | — | Primary key (unique ID) |
| `user_id` | String | No | — | Creator reference |
| `name` | String | No | — | Display name |
| `content` | Text | No | — | OpenAPI YAML specification |
| `specs` | JSON | Yes | `[]` | Parsed specification |
| `meta` | JSON | Yes | `{}` | Description, manifest |
| `valves` | JSON | Yes | `{}` | Configuration parameters |
| `access_control` | JSON | Yes | — | Access rules |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_tools_user_id`

---

## Table: models

Model configurations and aliases.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String | No | — | Primary key (model identifier) |
| `user_id` | String | Yes | — | Creator (null for system) |
| `base_model_id` | String | Yes | — | Underlying model (for aliases) |
| `name` | String | No | — | Display name |
| `params` | JSON | Yes | `{}` | Parameter overrides |
| `meta` | JSON | Yes | `{}` | Description, capabilities |
| `access_control` | JSON | Yes | — | Access rules |
| `is_active` | Boolean | No | `True` | Available for use |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id` (nullable)

**Indexes:**
- `ix_models_user_id`

---

## Table: feedbacks

User feedback on model responses.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | User who provided feedback |
| `type` | String | No | — | `rating` or `comparison` |
| `data` | JSON | No | — | Feedback data (rating, model_ids) |
| `meta` | JSON | Yes | `{}` | Context (chat_id, message_id) |
| `snapshot` | JSON | Yes | — | Response snapshot |
| `version` | Integer | No | `0` | Schema version |
| `created_at` | BigInteger | No | `now()` | Feedback timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_feedbacks_user_id`
- `ix_feedbacks_type`

---

## Table: oauth_sessions

OAuth token storage (encrypted).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | String (UUID) | No | — | Primary key |
| `user_id` | String | No | — | User reference |
| `provider` | String | No | — | OAuth provider name |
| `token` | Text | No | — | Encrypted token data |
| `expires_at` | BigInteger | Yes | — | Token expiration |
| `created_at` | BigInteger | No | `now()` | Creation timestamp |
| `updated_at` | BigInteger | No | `now()` | Last update timestamp |

**Foreign Keys:**
- `user_id` → `users.id`

**Indexes:**
- `ix_oauth_sessions_user_id`
- `ix_oauth_sessions_provider`

**Security:** Token field encrypted with Fernet using `OAUTH_SESSION_TOKEN_ENCRYPTION_KEY`.

---

## Additional Tables

### folders

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `user_id` | String | Owner |
| `name` | String | Folder name |
| `parent_id` | String | Parent folder (self-referential) |
| `is_expanded` | Boolean | UI state |
| `data` | JSON | Additional data |
| `meta` | JSON | Metadata |
| `created_at` | BigInteger | Creation timestamp |
| `updated_at` | BigInteger | Last update |

### tags

| Column | Type | Description |
|--------|------|-------------|
| `id` | String | Normalized tag name (PK) |
| `name` | String | Display name |
| `user_id` | String | Owner |
| `meta` | JSON | Metadata |
| `created_at` | BigInteger | Creation timestamp |

### notes

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `user_id` | String | Owner |
| `title` | String | Note title |
| `data` | JSON | Note content |
| `meta` | JSON | Metadata |
| `access_control` | JSON | Access rules |
| `created_at` | BigInteger | Creation timestamp |
| `updated_at` | BigInteger | Last update |

### channel_webhooks

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (UUID) | Primary key |
| `channel_id` | String | Channel reference |
| `user_id` | String | Creator |
| `name` | String | Webhook name |
| `token` | String | Webhook token |
| `profile_image_url` | String | Bot avatar |
| `last_used_at` | BigInteger | Last usage |
| `created_at` | BigInteger | Creation timestamp |
| `updated_at` | BigInteger | Last update |

---

## Related Documents

- `DATA_MODEL.md` — Conceptual entity relationships
- `DOMAIN_GLOSSARY.md` — Term definitions
- `DIRECTIVE_database_migration.md` — How to modify schema

---

*Last updated: 2026-02-03*
