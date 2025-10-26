# Backend Models Directory

This directory contains the data persistence and ORM layer for Open WebUI, providing database schema definitions, Pydantic validation models, and data access objects (DAOs) for all core entities.

## Files

### auths.py
- `Auth` (SQLAlchemy model) - Authentication credentials storage
- `AuthsTable.insert_new_auth()` - Creates auth + user atomically
- `AuthsTable.authenticate_user()` - Email/password validation
- `AuthsTable.authenticate_user_by_api_key()` - API key lookup

**Used by:**
- `routers/auths.py` - Signin, signup, password management
- `utils/auth.py` - get_verified_user() dependency injection

**Uses:**
- `models/users.py` - Creates User on signup
- `internal/db.py` - Database session management

### users.py
- `User` (SQLAlchemy model) - User profiles with settings/info JSON fields
- `UsersTable.insert_new_user()` - User creation
- `UsersTable.update_user_settings_by_id()` - Preferences management
- `UsersTable.delete_user_by_id()` - Cascading deletion

**Used by:**
- `routers/users.py` - User CRUD operations
- `routers/auths.py` - Session management
- All routers via `get_verified_user()` dependency

**Uses:**
- `models/chats.py` - Cascading chat deletion
- `models/groups.py` - Group membership cleanup

### chats.py
- `Chat` (SQLAlchemy model) - Chat history with nested JSON messages
- `ChatsTable.insert_new_chat()` - New conversation
- `ChatsTable.upsert_message_to_chat_by_id_and_message_id()` - Incremental message updates
- `ChatsTable.get_chats_by_user_id_and_search_text()` - Database-agnostic JSON querying

**Used by:**
- `routers/chats.py` - Chat CRUD, search, sharing
- `socket/main.py` - Real-time message updates

**Uses:**
- `models/tags.py` - Tag associations
- `models/folders.py` - Folder organization

### files.py
- `File` (SQLAlchemy model) - File metadata with hash tracking
- `FilesTable.insert_new_file()` - File registration
- `FilesTable.get_file_by_id()` - File retrieval

**Used by:**
- `routers/files.py` - Upload/download operations
- `routers/retrieval.py` - Document processing

**Uses:**
- `storage/provider.py` - Physical file storage (not direct import)

### knowledge.py
- `Knowledge` (SQLAlchemy model) - Knowledge base/RAG collections
- `KnowledgesTable.get_knowledge_bases()` - List with access control
- Data field stores vector DB metadata

**Used by:**
- `routers/knowledge.py` - Knowledge base management
- `routers/retrieval.py` - RAG queries

**Uses:**
- `models/files.py` - File associations
- `utils/access_control.py` - Permission filtering

### tools.py, functions.py
- Tool/Function definitions with valve (configuration) system
- Global valves + per-user overrides stored in User.settings
- `get_user_valves_by_id_and_user_id()` - Hierarchical config lookup

**Used by:**
- `routers/tools.py`, `routers/functions.py` - Management interfaces
- Chat completion pipeline for function calling

**Uses:**
- `models/users.py` - User valve storage

### prompts.py
- `Prompt` (SQLAlchemy model) - Slash command templates
- Command is primary key (e.g., `/summarize`)

**Used by:**
- `routers/prompts.py` - Template CRUD
- Chat input parsing for command expansion

### models.py (LLM Models)
- `Model` (SQLAlchemy model) - Custom model configurations
- `base_model_id` - Optional model proxying
- `access_control` - Permission matrix

**Used by:**
- `routers/models.py` - Model management
- Chat completions for model selection

### Other Models
- `channels.py`, `messages.py` - Team communication
- `notes.py` - Note-taking with collaborative editing
- `folders.py` - Hierarchical chat organization
- `memories.py` - Persistent user context
- `feedbacks.py` - User feedback collection
- `tags.py` - Chat categorization (composite PK: id+user_id)
- `groups.py` - User grouping for permissions
- `token_usage.py` - Token quota tracking (custom fork feature)

## Architecture & Patterns

### DAO/Repository Pattern
Every model has a `*Table` class singleton:
- Encapsulates all database queries
- Methods follow naming: `{verb}_{entity}_by_{field}`
- Example: `Chats = ChatsTable()` (singleton instance)

### JSON Field Usage
- **Nested Data**: `chat.history.messages`, `user.settings`
- **Metadata**: `meta.tags`, `meta.capabilities`
- **Access Control**: `access_control.{read,write}.{user_ids,group_ids}`
- **Valves**: Tool/function parameters stored as flat JSON

### Timestamp Conventions
- **Standard (epoch seconds)**: Most models use `int(time.time())`
- **Nanoseconds**: Channels, Messages, Notes use `int(time.time_ns())`

### Database Compatibility
- Conditional SQL for SQLite vs PostgreSQL
- JSON queries use dialect-specific functions (json_each vs json_array_elements)

## Integration Points

### Router Layer
Routers import model singletons and use context manager pattern:
```python
with get_db() as db:
    Chats.insert_new_chat(user_id, form_data)
```

### Authentication Flow
```
POST /auth/signin → routers/auths.py
  → Auths.authenticate_user(email, password)
    → Users.get_user_by_email()
    → Password verification
    → Returns UserModel
  → JWT token generation
```

### Chat Creation Flow
```
POST /chats → routers/chats.py
  → Chats.insert_new_chat(user_id, ChatForm)
    → Creates chat with empty nested history
  → Socket broadcast to user sessions
```

### Cascading Deletion
```
DELETE /users/{id} → Users.delete_user_by_id(id)
  → Groups.remove_user_from_all_groups(id)
  → Chats.delete_chats_by_user_id(id)
  → Auths deletion
  → User deletion
```

## Key Workflows

### Access Control Pattern
```
Models filtered by:
  - Owner check: model.user_id == user.id
  - OR has_access(user_id, "read", model.access_control)
```

### Valve (Configuration) Override Pattern
```
Tool valve hierarchy:
  1. Global: Tool.valves (shared)
  2. User override: User.settings.tools.valves[tool_id]
Get via Tools.get_user_valves_by_id_and_user_id()
```

### Chat History Structure
- Entire message history in single JSON field
- Nested structure: `chat.history.messages{id: {...}}`
- Upsert loads entire chat, modifies in-memory, writes back
- Database-specific JSON parsing for search

## Important Notes

**Critical Dependencies:**
- All models depend on `internal/db.py` for Base and get_db
- JSONField from `internal/db.py` for flexible schema
- No explicit foreign key constraints; referential integrity handled in application layer

**Performance Considerations:**
- Chat search complexity: Full JSON load for each search hit
- Group membership queries: O(n) JSON array scans
- No indexes on JSON fields; filtering done in Python

**Data Integrity:**
- No foreign keys at database level
- Orphaned records possible if deletions bypass model layer
- Concurrent updates may conflict (last-write-wins)
