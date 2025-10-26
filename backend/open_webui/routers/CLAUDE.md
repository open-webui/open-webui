# Backend Routers Directory

This directory contains all FastAPI route handlers (API endpoints) for Open WebUI, providing the REST API interface between the frontend and backend business logic. Each router file corresponds to a specific domain (chats, users, models, etc.) and handles HTTP request/response cycles with authentication, validation, and access control.

## Major Router Files

### auths.py (Authentication & Admin Config)
- `signin()`, `signup()` - User authentication (supports local, LDAP, OAuth, trusted headers)
- `get_session_user()` - Current user with permissions
- `generate_api_key()`, `delete_api_key()` - API key lifecycle
- `get_admin_config()`, `update_admin_config()` - System configuration

**Backend APIs:**
- `POST /api/auths/signin` - Email/password or LDAP authentication
- `POST /api/auths/signup` - New user registration
- `GET /api/auths/` - Session user details
- `POST /api/auths/api_key` - Generate API key
- `GET /api/auths/admin/config` - Admin configuration

**Uses:**
- `models/auths.py` - Auths.authenticate_user()
- `models/users.py` - Users.insert_new_user()
- `utils/auth.py` - create_token(), get_password_hash()

**Returns to Frontend:**
- SessionUserResponse with token and permissions
- Admin config with version, features, OAuth providers

### users.py (User Management)
- `get_users()` - Paginated user listing with filtering
- `update_user_by_id()` - Admin user updates (role, password, settings)
- `delete_user_by_id()` - User deletion with primary admin protection
- `get/update_user_settings()` - UI preferences

**Backend APIs:**
- `GET /api/users` - List users (admin only)
- `GET /api/users/user/settings` - User settings
- `PUT /api/users/user/settings` - Update settings
- `DELETE /api/users/{id}` - Delete user

**Uses:**
- `models/users.py` - User CRUD operations
- `socket/main.py` - get_active_user_ids() for presence
- `utils/access_control.py` - Permission management

### chats.py (Chat Management)
- `create_new_chat()`, `get_chat_by_id()` - Chat CRUD
- `search_user_chats()` - Text search with tag filtering
- `share_chat_by_id()`, `delete_shared_chat_by_id()` - Sharing
- `add/delete_tag_by_id()` - Tag management with orphan cleanup
- `pin/archive_chat_by_id()` - State management

**Backend APIs:**
- `POST /api/chats` - Create chat
- `GET /api/chats` - List chats (paginated)
- `GET /api/chats/search` - Search with tags
- `POST /api/chats/{id}/share` - Create share link
- `POST /api/chats/{id}/tags` - Add tag

**Uses:**
- `models/chats.py` - Chat storage and querying
- `socket/main.py` - get_event_emitter() for real-time updates

**WebSocket Integration:**
- Emits `chat-events` on message updates
- Sends completion events, title generation, tag generation

### models.py (Model Management)
- `get_models()` - List available models with access control
- `create_new_model()`, `update_model_by_id()` - Custom models
- `toggle_model_by_id()` - Enable/disable

**Backend APIs:**
- `GET /api/models` - List models
- `POST /api/models/create` - Create custom model
- `POST /api/models/id/{id}/toggle` - Toggle model

**Uses:**
- `models/models.py` - Model storage
- `utils/access_control.py` - has_access() checks

### files.py (File Management)
- `upload_file()` - Multipart file upload with processing
- `get_file_content_by_id()` - Stream/download files
- `delete_file_by_id()` - File deletion with vector DB cleanup

**Backend APIs:**
- `POST /api/files` - Upload file
- `GET /api/files/{id}/content` - Download file
- `DELETE /api/files/{id}` - Delete file

**Uses:**
- `storage/provider.py` - Storage.upload_file(), get_file()
- `routers/retrieval.py` - process_file() for embeddings
- `retrieval/vector/factory.py` - VECTOR_DB_CLIENT.delete()

### retrieval.py (RAG/Document Processing)
- `process_file()` - Document chunking and embedding
- `process_web_search()` - Web search + embedding
- `query_collection()` - Multi-collection semantic search
- `get/update_rag_config()` - RAG configuration

**Backend APIs:**
- `POST /api/retrieval/process/file` - Process uploaded file
- `POST /api/retrieval/web/search` - Web search
- `POST /api/retrieval/query/collection` - Semantic search
- `GET /api/retrieval/config` - RAG settings

**Uses:**
- `retrieval/loaders/main.py` - Loader for document extraction
- `retrieval/vector/factory.py` - VECTOR_DB_CLIENT for embeddings
- `retrieval/web/` - Web search engines

**RAG Pipeline:**
```
File Upload
  ↓
process_file(file_id, collection_name)
  ↓
Loader.load() → Extract text
  ↓
Text splitter → Chunks
  ↓
get_embedding_function() → Embeddings
  ↓
VECTOR_DB_CLIENT.insert() → Store vectors
```

### openai.py, ollama.py (LLM Integrations)
- `chatCompletion()` - Streaming chat completions
- `generateChatCompletion()` - Proxied LLM calls
- Model parameter injection, system prompt application

**Backend APIs:**
- `POST /api/chat/completions` - OpenAI-compatible completions
- `GET /ollama/api/tags` - Ollama model list
- `POST /ollama/api/chat` - Ollama streaming chat

**Uses:**
- `models/models.py` - Model configurations
- `utils/payload.py` - apply_model_params_to_body()

### knowledge.py (Knowledge Bases)
- `create_new_knowledge()`, `get_knowledge_bases()` - KB management
- `add_file_to_knowledge_by_id()` - File associations
- `reindex_knowledge_files()` - Re-embedding after config changes

**Backend APIs:**
- `POST /api/knowledge` - Create knowledge base
- `GET /api/knowledge` - List knowledge bases
- `POST /api/knowledge/{id}/file/add` - Add file

**Uses:**
- `models/knowledge.py` - Knowledge storage
- `routers/retrieval.py` - process_file() for embeddings

### tools.py, functions.py (Extensibility)
- Tool/function CRUD with valve (configuration) management
- `get/update_tools_valves_by_id()` - Global config
- `get/update_tools_user_valves_by_id()` - Per-user overrides

**Backend APIs:**
- `POST /api/tools` - Create tool
- `GET /api/tools/{id}/valves` - Get tool config
- `POST /api/tools/{id}/valves/update` - Update config

**Uses:**
- `models/tools.py`, `models/functions.py`
- `utils/plugin.py` - load_tool_module_by_id()

## Architecture & Patterns

### Consistent Endpoint Pattern
```python
@router.post("/resource")
async def create_resource(
    form_data: ResourceForm,
    user=Depends(get_verified_user)
):
    # 1. Authorization check
    if user.role != "admin" and not has_permission(...):
        raise HTTPException(status_code=401)

    # 2. Business logic via models
    resource = Resources.insert_new_resource(user.id, form_data)

    # 3. Optional socket broadcast
    await get_event_emitter()(event_data)

    # 4. Return Pydantic model
    return ResourceResponse(**resource)
```

### Authentication/Authorization Pattern
- `get_verified_user` - Any authenticated user
- `get_admin_user` - Admin only
- Permission checks: `user.role == "admin"` OR `has_permission(user.id, "scope", config)`

### Error Handling
- HTTPException with appropriate status codes
- ERROR_MESSAGES constants for user-facing messages
- Logging via SRC_LOG_LEVELS configuration

## Integration Points

### Frontend API Calls
Frontend components in `src/lib/apis/` consume these endpoints:
- `src/lib/apis/chats/index.ts` → `/api/chats`
- `src/lib/apis/users/index.ts` → `/api/users`
- `src/lib/apis/files/index.ts` → `/api/files`
- `src/lib/apis/retrieval/index.ts` → `/api/retrieval`

### WebSocket Events
Routers emit events via socket:
```python
emit_fn = get_event_emitter(request_info)
await emit_fn({
    "type": "chat:completion",
    "data": {"content": "...", "done": true}
})
```

Frontend receives via:
```javascript
socket.on('chat-events', (data) => {
    // Handle completion, title, tags, etc.
})
```

### Model Layer
All routers use models via context manager:
```python
with get_db() as db:
    result = Chats.insert_new_chat(user_id, form)
```

## Key Workflows

### Chat Message Flow
```
POST /api/chat/completions
  ↓
Router validates auth + parameters
  ↓
Apply model parameters + system prompt
  ↓
Call LLM backend (OpenAI/Ollama)
  ↓
Stream response via socket 'chat-events'
  ↓
Frontend receives delta events
  ↓
POST /api/chat/completed (analytics)
```

### File Upload + RAG Flow
```
POST /api/files (multipart)
  ↓
Storage.upload_file() → Save to disk/cloud
  ↓
Files.insert_new_file() → Database record
  ↓
process_file() → Extract + chunk + embed
  ↓
VECTOR_DB_CLIENT.insert() → Vector storage
  ↓
Return FileModel with embedded metadata
```

### Knowledge Base Query Flow
```
POST /api/retrieval/query/collection
  ↓
Embedding function encodes query
  ↓
VECTOR_DB_CLIENT.search() → Top-k results
  ↓
Optional reranking
  ↓
Return SearchResult with documents + distances
```

## Important Notes

**Critical Dependencies:**
- All routers require models layer for persistence
- Socket integration optional but critical for real-time features
- Storage provider must be configured for file operations
- Vector DB required for RAG functionality

**Performance Considerations:**
- Streaming responses via async generators for chat completions
- Pagination on large list endpoints (chats, users)
- Background tasks for expensive operations (embedding, transcription)

**Security:**
- Token validation on every request via Depends(get_verified_user)
- Admin-only endpoints protected by get_admin_user
- Access control checks for shared resources
- File upload size limits and extension whitelists
