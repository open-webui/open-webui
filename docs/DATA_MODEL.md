# Data Model

> **Purpose:** Conceptual documentation of entity relationships, lifecycles, and design rationale
> **Audience:** Developers understanding data architecture, AI agents planning database changes
> **Usage:** Reference before modifying database schema or understanding entity connections

---

## Prerequisites

- `DOMAIN_GLOSSARY.md` — Term definitions for entities mentioned here

---

## Entity Relationship Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER DOMAIN                                         │
│                                                                                  │
│  ┌──────────┐ 1:1 ┌──────────┐      ┌──────────┐                               │
│  │   User   │────▶│   Auth   │      │  ApiKey  │◀──┐                           │
│  └──────────┘     └──────────┘      └──────────┘   │ 1:N                        │
│       │                                             │                            │
│       ├─────────────────────────────────────────────┘                            │
│       │                                                                          │
│       │ N:M (via GroupMember)                                                    │
│       ▼                                                                          │
│  ┌──────────┐ 1:N ┌─────────────┐                                               │
│  │  Group   │────▶│ GroupMember │                                               │
│  └──────────┘     └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONVERSATION DOMAIN                                    │
│                                                                                  │
│  User                                                                            │
│    │                                                                             │
│    │ 1:N                                                                         │
│    ▼                                                                             │
│  ┌──────────┐ 1:N ┌─────────────┐                                               │
│  │   Chat   │────▶│ ChatMessage │  (dual-write: also in Chat.chat JSON)         │
│  └──────────┘     └─────────────┘                                               │
│       │                                                                          │
│       │ N:M (via ChatFile)                                                       │
│       ▼                                                                          │
│  ┌──────────┐                                                                    │
│  │   File   │                                                                    │
│  └──────────┘                                                                    │
│       │                                                                          │
│       │ belongs to (optional)                                                    │
│       ▼                                                                          │
│  ┌──────────┐ self-referential (parent_id)                                      │
│  │  Folder  │◀─────────────────────────┐                                        │
│  └──────────┘                          │                                        │
│       ▲                                │                                        │
│       └────────────────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                             CHANNEL DOMAIN                                       │
│                                                                                  │
│  User                                                                            │
│    │                                                                             │
│    │ 1:N                                                                         │
│    ▼                                                                             │
│  ┌──────────┐ 1:N ┌───────────────┐                                             │
│  │ Channel  │────▶│ ChannelMember │                                             │
│  └──────────┘     └───────────────┘                                             │
│       │                                                                          │
│       │ 1:N                                                                      │
│       ▼                                                                          │
│  ┌──────────┐ 1:N ┌─────────────────┐                                           │
│  │ Message  │────▶│ MessageReaction │                                           │
│  └──────────┘     └─────────────────┘                                           │
│       │                                                                          │
│       │ self-referential (reply_to_id, parent_id)                               │
│       ▼                                                                          │
│  ┌──────────────┐                                                                │
│  │ChannelWebhook│                                                                │
│  └──────────────┘                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            KNOWLEDGE DOMAIN (RAG)                                │
│                                                                                  │
│  User                                                                            │
│    │                                                                             │
│    │ 1:N                                                                         │
│    ▼                                                                             │
│  ┌───────────┐ N:M ┌───────────────┐ N:1 ┌──────────┐                           │
│  │ Knowledge │────▶│ KnowledgeFile │────▶│   File   │                           │
│  └───────────┘     └───────────────┘     └──────────┘                           │
│                                                │                                 │
│                                                │ embeddings                      │
│                                                ▼                                 │
│                                          ┌───────────┐                          │
│                                          │ Vector DB │ (external)               │
│                                          └───────────┘                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION DOMAIN                                    │
│                                                                                  │
│  User                                                                            │
│    │                                                                             │
│    │ 1:N (each)                                                                  │
│    ├──────────────────────────────────────────────────────────────┐             │
│    │                    │                    │                    │             │
│    ▼                    ▼                    ▼                    ▼             │
│  ┌──────────┐     ┌──────────┐        ┌──────────┐         ┌──────────┐        │
│  │  Prompt  │     │ Function │        │   Tool   │         │  Model   │        │
│  └──────────┘     └──────────┘        └──────────┘         └──────────┘        │
│       │                                                                          │
│       │ 1:N (versioning)                                                         │
│       ▼                                                                          │
│  ┌──────────────┐                                                                │
│  │PromptHistory │                                                                │
│  └──────────────┘                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Entities

### User

**Purpose:** Central identity for authentication, authorization, and resource ownership.

**Key relationships:**
- **Owns:** Chat, File, Knowledge, Prompt, Function, Tool, Model, Note, Memory, Channel
- **Belongs to:** Group (via GroupMember)
- **Has one:** Auth (credentials)
- **Has many:** ApiKey (programmatic access)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `email` | String | Unique, used for login |
| `name` | String | Display name |
| `role` | Enum | Authorization level (admin/user/pending) |
| `settings` | JSON | User preferences |
| `oauth_sub` | String | OAuth subject identifier (for SSO) |

**Lifecycle:** Created (signup) → Active → Deleted (soft delete)

---

### Chat

**Purpose:** Container for a conversation session with message history.

**Key relationships:**
- **Belongs to:** User (owner)
- **Has many:** ChatMessage (analytics table)
- **Has many:** File (via ChatFile)
- **Belongs to:** Folder (optional organization)
- **Has many:** Tag (via meta.tags)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Owner reference |
| `title` | String | Display name (auto-generated or user-set) |
| `chat` | JSON | Full message history (legacy structure) |
| `share_id` | String | Public sharing identifier (nullable) |
| `archived` | Boolean | Soft archive flag |
| `pinned` | Boolean | Pin to top of list |
| `folder_id` | UUID | Organization folder (nullable) |

**Lifecycle:** Created → Active → Archived → Deleted

**Design decision:** The `chat` JSON field stores the complete message tree for backward compatibility. `ChatMessage` table provides normalized access for analytics. See `ADR_008_message_analytics.md`.

---

### ChatMessage

**Purpose:** Normalized storage of individual messages for efficient querying and analytics.

**Key relationships:**
- **Belongs to:** Chat
- **Belongs to:** User (who sent or received)
- **References:** Model (for assistant messages)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | Composite | `(chat_id, message_id)` |
| `role` | Enum | `user`, `assistant`, `system` |
| `content` | Text/JSON | Message content (string or structured) |
| `model_id` | String | Model that generated response |
| `usage` | JSON | Token consumption metrics |
| `status_history` | JSON | State transitions during streaming |

**Design decision:** Dual-write pattern maintains both this table and `Chat.chat` JSON. This enables analytics queries without breaking existing chat retrieval logic.

---

### Channel

**Purpose:** Real-time communication space for user-to-user messaging.

**Key relationships:**
- **Belongs to:** User (creator)
- **Has many:** ChannelMember (participants)
- **Has many:** Message (channel messages)
- **Has many:** ChannelWebhook (integrations)
- **Has many:** File (via ChannelFile)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `type` | Enum | `null`/`"group"` for group, `"dm"` for direct |
| `name` | String | Channel display name |
| `is_private` | Boolean | Visibility to non-members |
| `access_control` | JSON | Read/write permissions |
| `archived_at` | Timestamp | Soft archive |
| `deleted_at` | Timestamp | Soft delete |

**Lifecycle:** Created → Active → Archived → Deleted

---

### Knowledge

**Purpose:** Document collection for RAG (Retrieval-Augmented Generation).

**Key relationships:**
- **Belongs to:** User (owner)
- **Has many:** File (via KnowledgeFile)
- **References:** Vector DB (external, via embeddings)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `name` | String | Display name |
| `description` | Text | Purpose/contents description |
| `access_control` | JSON | Who can read/write |
| `meta` | JSON | Additional metadata |

**Data flow:**
1. File uploaded → added to Knowledge via KnowledgeFile
2. File content parsed by document loader
3. Text chunked and embedded
4. Embeddings stored in vector database
5. At query time: query embedded → similarity search → chunks retrieved

---

### File

**Purpose:** Storage reference for uploaded content (documents, images, etc.).

**Key relationships:**
- **Belongs to:** User (uploader)
- **Referenced by:** Chat (via ChatFile), Knowledge (via KnowledgeFile), Channel (via ChannelFile)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `hash` | String | Content hash (deduplication) |
| `filename` | String | Original file name |
| `path` | String | Storage location |
| `data` | JSON | Parsed content, metadata |
| `meta` | JSON | File type, size, etc. |
| `access_control` | JSON | Permissions |

**Storage:** Files stored in `backend/open_webui/storage/` (local) or S3-compatible storage.

---

### Model (Configuration)

**Purpose:** Model definition that can be a base model reference or custom alias with overrides.

**Key relationships:**
- **Belongs to:** User (creator, for custom models)
- **References:** Base model (via `base_model_id`)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | String | Model identifier (e.g., "gpt-4o") |
| `base_model_id` | String | Underlying model (for aliases) |
| `name` | String | Display name |
| `params` | JSON | Parameter overrides (temperature, etc.) |
| `meta` | JSON | Description, capabilities |
| `access_control` | JSON | Who can use this model |
| `is_active` | Boolean | Available for selection |

**Use cases:**
- Base model: `id="gpt-4o"`, `base_model_id=null`
- Alias: `id="fast-assistant"`, `base_model_id="gpt-4o-mini"`, custom params

---

### Prompt

**Purpose:** Reusable prompt template invoked via command.

**Key relationships:**
- **Belongs to:** User (creator)
- **Has many:** PromptHistory (versions)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `command` | String | Trigger command (e.g., "/summarize") |
| `content` | Text | Prompt template text |
| `version_id` | UUID | Current version reference |
| `access_control` | JSON | Sharing permissions |

**Versioning:** Each edit creates a `PromptHistory` snapshot. `version_id` points to current version. `parent_id` in history creates a linked list of versions.

---

### Function

**Purpose:** Custom Python code that extends platform capabilities.

**Key relationships:**
- **Belongs to:** User (creator)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | String | Unique identifier |
| `type` | Enum | `filter` or `action` |
| `content` | Text | Python source code |
| `valves` | JSON | Configuration parameters |
| `is_active` | Boolean | Currently enabled |
| `is_global` | Boolean | Applies to all users |

**Execution:** Code runs in RestrictedPython sandbox with limited capabilities.

---

### Tool

**Purpose:** External capability that models can invoke via function calling.

**Key relationships:**
- **Belongs to:** User (creator)

**Key fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `id` | String | Unique identifier |
| `content` | Text | OpenAPI specification (YAML) |
| `specs` | JSON | Parsed specification |
| `valves` | JSON | Configuration parameters |
| `access_control` | JSON | Who can use |

**Tool sources:**
1. Local tools (database-stored OpenAPI specs)
2. Tool servers (external OpenAPI endpoints)
3. MCP servers (Model Context Protocol)

---

## Access Control Model

Many entities share a common access control pattern:

```json
{
  "read": {
    "group_ids": ["group-uuid-1", "group-uuid-2"],
    "user_ids": ["user-uuid-1"]
  },
  "write": {
    "group_ids": ["group-uuid-1"],
    "user_ids": []
  }
}
```

**Applied to:** Knowledge, Model, Prompt, Tool, Channel, Note, File

**Evaluation logic:**
1. Owner always has full access
2. Admins bypass access control (configurable)
3. Check if user's ID in `user_ids`
4. Check if any of user's groups in `group_ids`
5. Deny if no match

**Implementation:** `backend/open_webui/utils/access_control.py`

---

## Lifecycle States

### Chat Lifecycle

```
┌─────────┐     ┌────────┐     ┌──────────┐     ┌─────────┐
│ Created │────▶│ Active │────▶│ Archived │────▶│ Deleted │
└─────────┘     └────────┘     └──────────┘     └─────────┘
                    │                               ▲
                    │         (restore)             │
                    └───────────────────────────────┘
```

### Channel Lifecycle

```
┌─────────┐     ┌────────┐     ┌──────────┐     ┌─────────┐
│ Created │────▶│ Active │────▶│ Archived │────▶│ Deleted │
└─────────┘     └────────┘     └──────────┘     └─────────┘
                                    │                ▲
                                    │  (soft delete) │
                                    └────────────────┘

Fields: archived_at, archived_by, deleted_at, deleted_by
```

### User Lifecycle

```
┌──────────┐     ┌─────────┐     ┌────────┐     ┌──────────┐
│ Pending  │────▶│ Active  │────▶│ Active │────▶│ Inactive │
│(if gated)│     │(role=   │     │(role=  │     │(deleted) │
└──────────┘     │ user)   │     │ admin) │     └──────────┘
                 └─────────┘     └────────┘
```

---

## Join Tables

### ChatFile
Links Chat to File for attachments in conversations.
- `chat_id` → Chat
- `file_id` → File

### KnowledgeFile
Links Knowledge base to File for RAG documents.
- `knowledge_id` → Knowledge
- `file_id` → File

### ChannelFile
Links Channel messages to File attachments.
- `channel_id` → Channel
- `message_id` → Message
- `file_id` → File

### GroupMember
Links User to Group for membership.
- `group_id` → Group
- `user_id` → User

### ChannelMember
Links User to Channel with membership details.
- `channel_id` → Channel
- `user_id` → User
- Additional: `role`, `status`, `last_read_at`

---

## Design Patterns

### Dual-Write Pattern

**Used in:** Chat / ChatMessage

The Chat entity stores complete message history in a JSON field (`chat`) for backward compatibility with existing code. Simultaneously, individual messages are written to the `ChatMessage` table for analytics queries.

**Rationale:** Enables analytics without breaking existing chat retrieval. See `ADR_008_message_analytics.md`.

### Soft Delete Pattern

**Used in:** Channel, potentially others

Entities are marked as deleted (`deleted_at` timestamp) rather than physically removed. This enables:
- Audit trails
- Recovery of accidentally deleted data
- Referential integrity preservation

### Versioning Pattern

**Used in:** Prompt / PromptHistory

Each edit creates a new history record with:
- `snapshot`: Complete state at that point
- `parent_id`: Link to previous version
- `commit_message`: Description of change

Enables rollback and change tracking.

### Access Control Pattern

**Used in:** Knowledge, Model, Prompt, Tool, Channel, Note, File

Consistent JSON structure for permissions across entities. Evaluated by centralized utility function.

---

## Related Documents

- `DATABASE_SCHEMA.md` — Field-level schema reference (generated)
- `DOMAIN_GLOSSARY.md` — Term definitions
- `ADR_008_message_analytics.md` — Chat/ChatMessage dual-write rationale

---

*Last updated: 2026-02-03*
