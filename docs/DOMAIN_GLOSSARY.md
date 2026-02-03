# Domain Glossary

> **Purpose:** Single source of truth for terminology mapping business concepts to code
> **Audience:** Developers, AI agents, new contributors
> **Usage:** Reference when encountering unfamiliar terms or understanding entity relationships

---

## Prerequisites

- `PRODUCT_OVERVIEW.md` — Understanding of Open WebUI features

---

## Table of Contents

1. [Core Entities & User Management](#1-core-entities--user-management)
2. [Conversation & Messaging](#2-conversation--messaging)
3. [Content Management & Knowledge](#3-content-management--knowledge)
4. [Configuration & Customization](#4-configuration--customization)
5. [Security & Authentication](#5-security--authentication)
6. [AI & Model Concepts](#6-ai--model-concepts)
7. [Data Structures & Patterns](#7-data-structures--patterns)
8. [System Operations](#8-system-operations)

---

## 1. Core Entities & User Management

### User

**Business meaning:** A person who has registered an account in Open WebUI. Users can chat with AI models, upload files, create knowledge bases, and collaborate in channels.

**Technical mapping:**
- **Database:** `users` table with `id` (UUID), `email`, `name`, `role`, `profile_image_url`, `settings`, `oauth_sub`
- **Model:** `backend/open_webui/models/users.py` → `User`, `UserModel`
- **API:** `backend/open_webui/routers/users.py`
- **Store:** `src/lib/stores/index.ts` → `user` writable

**Relationships:**
- Has one `Auth` record (credentials)
- Has many `ApiKey` records
- Has many `Chat` records
- Belongs to many `Group` records (via `GroupMember`)

---

### Auth

**Business meaning:** Authentication credentials for a user account, storing the hashed password and active status.

**Technical mapping:**
- **Database:** `auths` table with `id` (same as user_id), `email`, `password` (hashed), `active`
- **Model:** `backend/open_webui/models/auths.py` → `Auth`, `AuthModel`
- **API:** `backend/open_webui/routers/auths.py`

**When this matters:**
- User registration (`/api/v1/auths/signup`)
- Password authentication (`/api/v1/auths/signin`)
- Password changes and resets

---

### ApiKey

**Business meaning:** A long-lived token that allows programmatic access to the API without using a password. Used for integrations and automation.

**Technical mapping:**
- **Database:** `api_keys` table with `id`, `user_id`, `key` (hashed), `name`, `expires_at`, `last_used_at`
- **Model:** `backend/open_webui/models/auths.py` → `ApiKey`
- **API:** `backend/open_webui/routers/auths.py` → `/api/v1/auths/api_key`

**When this matters:**
- External tool integrations
- CI/CD pipelines accessing the API
- Mobile app authentication

---

### Group

**Business meaning:** A collection of users that share permissions. Groups enable team-based access control to models, knowledge bases, and other resources.

**Technical mapping:**
- **Database:** `groups` table with `id`, `user_id` (owner), `name`, `description`, `permissions`, `access_control`, `meta`
- **Model:** `backend/open_webui/models/groups.py` → `Group`, `GroupModel`
- **API:** `backend/open_webui/routers/groups.py`

**Relationships:**
- Has many `GroupMember` records
- Referenced by `access_control` JSON on many entities

---

### GroupMember

**Business meaning:** The association between a user and a group, indicating membership.

**Technical mapping:**
- **Database:** `group_members` table with `id`, `group_id`, `user_id`, `created_at`
- **Model:** `backend/open_webui/models/groups.py` → `GroupMember`

---

### Role

**Business meaning:** The authorization level of a user, determining what features and actions they can access.

**Technical mapping:**
- **Values:** `"admin"`, `"user"`, `"pending"`, `"webhook"`
- **Field:** `users.role`
- **Enforcement:** `backend/open_webui/utils/auth.py` → `get_admin_user`, `get_verified_user`

**Role capabilities:**
- `admin`: Full system access, user management, configuration
- `user`: Standard access to chat, files, knowledge bases
- `pending`: Awaiting admin approval (if signup requires approval)
- `webhook`: Special role for webhook-initiated actions

---

### UserSettings

**Business meaning:** User-specific preferences and configurations, including UI theme, default models, and feature-specific settings.

**Technical mapping:**
- **Database:** Stored in `users.settings` JSON field
- **Structure:** `{ ui: {...}, models: [...], functions: {...}, tools: {...}, valves: {...} }`
- **API:** `backend/open_webui/routers/users.py` → `/api/v1/users/{id}/settings`

---

## 2. Conversation & Messaging

### Chat

**Business meaning:** A conversation session between a user and one or more AI models. Contains the full message history and metadata.

**Technical mapping:**
- **Database:** `chats` table with `id`, `user_id`, `title`, `chat` (JSON), `share_id`, `archived`, `pinned`, `folder_id`, `meta`
- **Model:** `backend/open_webui/models/chats.py` → `Chat`, `ChatModel`
- **API:** `backend/open_webui/routers/chats.py`
- **Store:** `src/lib/stores/index.ts` → `chats`, `chatId`

**The `chat` JSON structure:**
```json
{
  "history": {
    "messages": {
      "msg-id-1": { "role": "user", "content": "..." },
      "msg-id-2": { "role": "assistant", "content": "..." }
    },
    "currentId": "msg-id-2"
  }
}
```

**Lifecycle:** Created → Active → Archived → Deleted (soft delete)

---

### ChatMessage

**Business meaning:** An individual message within a chat conversation, stored separately for analytics and efficient querying.

**Technical mapping:**
- **Database:** `chat_messages` table with composite key (`chat_id`, `message_id`), `user_id`, `role`, `content`, `model_id`, `usage`
- **Model:** `backend/open_webui/models/chat_messages.py` → `ChatMessage`
- **Pattern:** Dual-write with `Chat.chat` JSON for backward compatibility

**When this matters:**
- Analytics queries (token usage, model utilization)
- Message-level search and filtering
- Usage tracking and billing

---

### Channel

**Business meaning:** A communication space for real-time messaging between users. Can be group chat, direct message (DM), or announcement channel.

**Technical mapping:**
- **Database:** `channels` table with `id`, `user_id`, `type`, `name`, `description`, `is_private`, `access_control`
- **Model:** `backend/open_webui/models/channels.py` → `Channel`, `ChannelModel`
- **API:** `backend/open_webui/routers/channels.py`
- **WebSocket:** `backend/open_webui/socket/main.py` → channel events

**Channel types:**
- `null` / `"group"`: Multi-user group channel
- `"dm"`: Direct message between two users

---

### Message (Channel Message)

**Business meaning:** A message posted in a channel (distinct from ChatMessage which is AI conversation).

**Technical mapping:**
- **Database:** `messages` table with `id`, `user_id`, `channel_id`, `content`, `reply_to_id`, `parent_id`, `is_pinned`
- **Model:** `backend/open_webui/models/channels.py` → `Message`
- **Relationships:** Has many `MessageReaction` records

---

### MessageReaction

**Business meaning:** An emoji reaction on a channel message, tracking who reacted and when.

**Technical mapping:**
- **Database:** `message_reactions` table with `id`, `user_id`, `message_id`, `name` (emoji)
- **Model:** `backend/open_webui/models/channels.py` → `MessageReaction`

---

### ChannelMember

**Business meaning:** A user's membership in a channel, tracking their notification preferences and last read position.

**Technical mapping:**
- **Database:** `channel_members` table with `channel_id`, `user_id`, `role`, `status`, `is_active`, `last_read_at`
- **Model:** `backend/open_webui/models/channels.py` → `ChannelMember`

**Member statuses:** `"joined"`, `"left"`, `"invited"`

---

### ChannelWebhook

**Business meaning:** An incoming webhook that allows external services to post messages to a channel.

**Technical mapping:**
- **Database:** `channel_webhooks` table with `id`, `channel_id`, `name`, `token`, `last_used_at`
- **Model:** `backend/open_webui/models/channels.py` → `ChannelWebhook`
- **API:** `backend/open_webui/routers/channels.py` → webhook endpoints

---

## 3. Content Management & Knowledge

### Knowledge (Knowledge Base)

**Business meaning:** A collection of documents used for Retrieval-Augmented Generation (RAG). When referenced in a chat, relevant content is retrieved and injected into the AI's context.

**Technical mapping:**
- **Database:** `knowledge` table with `id`, `user_id`, `name`, `description`, `access_control`, `meta`
- **Model:** `backend/open_webui/models/knowledge.py` → `Knowledge`, `KnowledgeModel`
- **API:** `backend/open_webui/routers/knowledge.py`
- **Vector storage:** Embeddings stored in configured vector database

**Relationships:**
- Has many `File` records (via `KnowledgeFile` join table)

---

### KnowledgeFile

**Business meaning:** The association between a knowledge base and a file, indicating which documents are included in the knowledge base.

**Technical mapping:**
- **Database:** `knowledge_files` table with `knowledge_id`, `file_id`, `user_id`
- **Model:** `backend/open_webui/models/knowledge.py` → `KnowledgeFile`

---

### File

**Business meaning:** An uploaded file (document, image, etc.) that can be used in chats, knowledge bases, or channels.

**Technical mapping:**
- **Database:** `files` table with `id`, `user_id`, `hash` (content hash), `filename`, `path`, `data`, `meta`, `access_control`
- **Model:** `backend/open_webui/models/files.py` → `File`, `FileModel`
- **API:** `backend/open_webui/routers/files.py`
- **Storage:** `backend/open_webui/storage/` (local or S3)

**Supported types:** PDF, DOCX, PPTX, TXT, MD, HTML, CSV, and 15+ more

---

### Memory

**Business meaning:** Persistent context about a user that the AI can recall across conversations. Used for personalization and continuity.

**Technical mapping:**
- **Database:** `memories` table with `id`, `user_id`, `content` (text)
- **Model:** `backend/open_webui/models/memories.py` → `Memory`
- **API:** `backend/open_webui/routers/memories.py`

**When this matters:**
- AI remembering user preferences
- Accumulating context over multiple sessions
- Personalized responses

---

### Note

**Business meaning:** A rich-text document created by a user, supporting collaborative editing.

**Technical mapping:**
- **Database:** `notes` table with `id`, `user_id`, `title`, `data` (content), `access_control`
- **Model:** `backend/open_webui/models/notes.py` → `Note`
- **API:** `backend/open_webui/routers/notes.py`
- **Collaboration:** YCRDT via WebSocket for real-time sync

---

### Folder

**Business meaning:** An organizational container for grouping chats. Supports nested hierarchies.

**Technical mapping:**
- **Database:** `folders` table with `id`, `user_id`, `name`, `parent_id` (for nesting), `is_expanded`
- **Model:** `backend/open_webui/models/folders.py` → `Folder`
- **API:** `backend/open_webui/routers/folders.py`

---

### Tag

**Business meaning:** A user-created label for organizing and filtering chats.

**Technical mapping:**
- **Database:** `tags` table with `id` (normalized name), `name`, `user_id`
- **Model:** `backend/open_webui/models/tags.py` → `Tag`
- **Usage:** Stored in `Chat.meta.tags`

---

## 4. Configuration & Customization

### Prompt

**Business meaning:** A reusable prompt template that can be invoked by a command (e.g., `/summarize`). Supports versioning.

**Technical mapping:**
- **Database:** `prompts` table with `id`, `user_id`, `command` (unique), `name`, `content`, `access_control`, `version_id`
- **Model:** `backend/open_webui/models/prompts.py` → `Prompt`, `PromptModel`
- **API:** `backend/open_webui/routers/prompts.py`

**Versioning:** Each edit creates a `PromptHistory` record for rollback

---

### PromptHistory

**Business meaning:** A version snapshot of a prompt, enabling history tracking and rollback.

**Technical mapping:**
- **Database:** `prompt_history` table with `id`, `prompt_id`, `parent_id`, `snapshot` (JSON), `commit_message`
- **Model:** `backend/open_webui/models/prompts.py` → `PromptHistory`

---

### Function

**Business meaning:** A custom Python function that extends Open WebUI's capabilities. Can be a filter (modifies requests/responses) or an action (performs operations).

**Technical mapping:**
- **Database:** `functions` table with `id`, `user_id`, `name`, `type`, `content` (Python code), `meta`, `valves`, `is_active`, `is_global`
- **Model:** `backend/open_webui/models/functions.py` → `Function`
- **API:** `backend/open_webui/routers/functions.py`
- **Execution:** RestrictedPython sandbox

**Function types:**
- `filter`: Intercepts and modifies request/response
- `action`: Performs an operation when triggered

---

### Tool

**Business meaning:** A capability that AI models can invoke during conversations. Defined via OpenAPI specifications.

**Technical mapping:**
- **Database:** `tools` table with `id`, `user_id`, `name`, `content` (OpenAPI YAML), `specs`, `meta`, `access_control`, `valves`
- **Model:** `backend/open_webui/models/tools.py` → `Tool`, `ToolModel`
- **API:** `backend/open_webui/routers/tools.py`

**Tool sources:**
- Local tools (stored in database)
- OpenAPI tool servers (external)
- MCP tool servers (Model Context Protocol)

---

### Model (Configuration)

**Business meaning:** A model configuration that can be a base model from a provider or a custom alias with parameter overrides.

**Technical mapping:**
- **Database:** `models` table with `id` (model name), `user_id`, `base_model_id`, `name`, `params`, `meta`, `access_control`, `is_active`
- **Model:** `backend/open_webui/models/models.py` → `Model`, `ModelModel`
- **API:** `backend/open_webui/routers/models.py`
- **Store:** `src/lib/stores/index.ts` → `models`

**Use cases:**
- Create model aliases (e.g., "fast-gpt" → "gpt-4o-mini")
- Override default parameters
- Restrict model access to specific groups

---

### Valves

**Business meaning:** Configuration parameters for functions and tools that can be adjusted without modifying code.

**Technical mapping:**
- **Field:** `functions.valves`, `tools.valves` (JSON)
- **Structure:** Key-value configuration specific to each function/tool
- **API:** Endpoint per function/tool for valve updates

---

## 5. Security & Authentication

### JWT Token

**Business meaning:** A stateless authentication token used for API access. Contains user identity and expiration.

**Technical mapping:**
- **Generation:** `backend/open_webui/utils/auth.py` → `create_token()`
- **Validation:** `backend/open_webui/utils/auth.py` → `decode_token()`
- **Usage:** `Authorization: Bearer <token>` header
- **Secret:** `WEBUI_SECRET_KEY` environment variable

---

### OAuthSession

**Business meaning:** Encrypted storage of OAuth tokens from external identity providers, enabling refresh and logout.

**Technical mapping:**
- **Database:** `oauth_sessions` table with `id`, `user_id`, `provider`, `token` (encrypted), `expires_at`
- **Model:** `backend/open_webui/models/oauth_sessions.py` → `OAuthSession`
- **Encryption:** Fernet cipher with `OAUTH_SESSION_TOKEN_ENCRYPTION_KEY`

---

### Access Control

**Business meaning:** A permission model that specifies which users and groups can read or write a resource.

**Technical mapping:**
- **Structure:** `{ "read": { "group_ids": [...], "user_ids": [...] }, "write": { "group_ids": [...], "user_ids": [...] } }`
- **Field:** `access_control` JSON on Knowledge, Model, Prompt, Tool, Channel, Note, File
- **Enforcement:** `backend/open_webui/utils/access_control.py`

---

## 6. AI & Model Concepts

### Provider

**Business meaning:** An external service that provides AI model inference (e.g., OpenAI, Ollama, Anthropic).

**Technical mapping:**
- **Configuration:** `backend/open_webui/config.py` → `OPENAI_API_BASE_URLS`, `OLLAMA_BASE_URLS`
- **Routers:** `backend/open_webui/routers/openai.py`, `ollama.py`
- **Store:** `src/lib/stores/index.ts` → connection state

**Supported providers:** OpenAI, Ollama, Anthropic, Google Gemini, Azure OpenAI, LM Studio, any OpenAI-compatible API

---

### RAG (Retrieval-Augmented Generation)

**Business meaning:** A technique that enhances AI responses by retrieving relevant documents and injecting them into the context.

**Technical mapping:**
- **Pipeline:** `backend/open_webui/retrieval/`
- **Loaders:** `backend/open_webui/retrieval/loaders/` (document parsing)
- **Vector DB:** `backend/open_webui/retrieval/vector/` (embedding storage)
- **API:** `backend/open_webui/routers/retrieval.py`

**Flow:** Query → Embed → Similarity search → Top-k chunks → Inject into prompt

---

### Embedding

**Business meaning:** A numerical vector representation of text, used for semantic similarity search.

**Technical mapping:**
- **Model:** Configured via `RAG_EMBEDDING_MODEL` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- **Storage:** Vector database (ChromaDB, Qdrant, etc.)
- **Generation:** `backend/open_webui/retrieval/` embedding utilities

---

### Vector Database

**Business meaning:** A database optimized for storing and searching vector embeddings.

**Technical mapping:**
- **Configuration:** `VECTOR_DB` environment variable
- **Options:** ChromaDB (default), Qdrant, Pinecone, Weaviate, Milvus, OpenSearch
- **Integration:** `backend/open_webui/retrieval/vector/`

---

### Pipeline

**Business meaning:** A processing flow for AI requests, potentially including pre-processing, model inference, and post-processing.

**Technical mapping:**
- **Middleware:** `backend/open_webui/utils/middleware.py`
- **Pipelines:** Custom pipeline definitions (if enabled)
- **Functions:** Filter functions that modify the pipeline

---

### Feedback

**Business meaning:** User ratings and comparisons of model responses, used for evaluation and leaderboards.

**Technical mapping:**
- **Database:** `feedbacks` table with `id`, `user_id`, `type`, `data`, `meta`, `snapshot`
- **Model:** `backend/open_webui/models/feedbacks.py` → `Feedback`
- **API:** `backend/open_webui/routers/evaluations.py`

**Feedback types:**
- `rating`: Score for a single response
- `comparison`: Preference between two model responses (arena)

---

## 7. Data Structures & Patterns

### JSONField

**Business meaning:** A database column type that stores arbitrary JSON data, used for flexible schemas.

**Technical mapping:**
- **Definition:** `backend/open_webui/internal/db.py` → `JSONField`
- **Dialect support:** SQLite (JSON1), PostgreSQL (JSONB), MySQL (JSON)
- **Usage:** `settings`, `meta`, `data`, `access_control` fields

---

### Meta

**Business meaning:** A JSON field for storing arbitrary metadata about an entity that doesn't fit in structured columns.

**Technical mapping:**
- **Field:** `meta` on Chat, Channel, File, Function, Tool, Model, Knowledge
- **Contents:** Entity-specific (e.g., description, manifest, tags)

---

### Data

**Business meaning:** A JSON field for storing entity-specific business data, often model or feature configuration.

**Technical mapping:**
- **Field:** `data` on Chat, Prompt, Channel, Note
- **Contents:** Feature-specific structured data

---

### Snapshot

**Business meaning:** A point-in-time copy of an entity's complete state, used for versioning and history.

**Technical mapping:**
- **Field:** `snapshot` on PromptHistory, Feedback
- **Contents:** Complete JSON serialization of the entity at that moment

---

### Status History

**Business meaning:** A timestamped log of status changes, tracking entity state transitions.

**Technical mapping:**
- **Field:** `status_history` on ChatMessage
- **Structure:** `[{ "status": "pending", "timestamp": 1234567890 }, ...]`

---

### Dual-Write Pattern

**Business meaning:** Writing the same data to two locations for backward compatibility and different access patterns.

**Technical mapping:**
- **Example:** ChatMessage table + Chat.chat JSON
- **Purpose:** Analytics queries use ChatMessage; legacy code uses Chat.chat
- **See:** `ADR_008_message_analytics.md`

---

### Soft Delete

**Business meaning:** Marking entities as deleted without physically removing them from the database.

**Technical mapping:**
- **Fields:** `archived_at`, `deleted_at`, `archived_by`, `deleted_by`
- **Applied to:** Channel, potentially others
- **Query pattern:** Filter by `deleted_at IS NULL`

---

## 8. System Operations

### Usage

**Business meaning:** Token consumption tracking for a model call, used for analytics and billing.

**Technical mapping:**
- **Field:** `ChatMessage.usage`
- **Structure:** `{ "input_tokens": N, "output_tokens": N, "total_tokens": N }`
- **Analytics:** `backend/open_webui/routers/analytics.py`

---

### Session Pool

**Business meaning:** In-memory storage of active WebSocket connections, mapping socket IDs to user data.

**Technical mapping:**
- **Variable:** `backend/open_webui/socket/main.py` → `SESSION_POOL`
- **Distributed:** `RedisDict` when `WEBSOCKET_MANAGER=redis`

---

### Usage Pool

**Business meaning:** Real-time tracking of which models are currently in use, for live utilization display.

**Technical mapping:**
- **Variable:** `backend/open_webui/socket/main.py` → `USAGE_POOL`
- **Structure:** `{ model_id: { socket_id: { "updated_at": timestamp } } }`

---

### Middleware

**Business meaning:** Request/response processing layer that handles cross-cutting concerns like authentication, logging, and transformation.

**Technical mapping:**
- **File:** `backend/open_webui/utils/middleware.py`
- **Functions:** Request modification, response streaming, usage logging

---

### Circuit Breaker

**Business meaning:** A pattern that prevents repeated calls to a failing service, allowing graceful degradation.

**Technical mapping:**
- **Usage:** AI service fallbacks when provider is unavailable
- **Implementation:** Service-level retry logic with exponential backoff

---

### Timestamp

**Business meaning:** A point in time, stored as Unix epoch (seconds or nanoseconds since 1970).

**Technical mapping:**
- **Type:** `BigInteger` in SQLAlchemy
- **Fields:** `created_at`, `updated_at`, `last_active_at`, `last_used_at`, `expires_at`
- **Utilities:** `backend/open_webui/utils/` time helpers

---

## Related Documents

- `DATA_MODEL.md` — Entity relationship diagrams and lifecycle states
- `DATABASE_SCHEMA.md` — Field-level schema reference
- `ARCHITECTURE_OVERVIEW.md` — System design patterns

---

*Last updated: 2026-02-03*
*Term count: 43 entries across 8 categories*
