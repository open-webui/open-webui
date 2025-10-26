# Frontend APIs Directory

This directory provides the abstraction layer between the SvelteKit frontend and the FastAPI backend, wrapping all HTTP API calls with typed TypeScript functions. It handles authentication, request formatting, error handling, and response parsing, serving as the single source of truth for backend communication patterns.

## Directory Structure

### index.ts
Central exports file re-exporting all API modules for convenient imports.

**Exports:**
- All functions from subdirectory API modules
- Constants: WEBUI_API_BASE_URL, WEBUI_BASE_URL

**Used by:**
- ALL Svelte components and routes making API calls
- Import pattern: `import { getChatById, getModels } from '$lib/apis'`

### auths/index.ts
Authentication and session management API calls.

**Key Functions:**
- `signinUser(email, password)` - POST /api/auths/signin
- `signupUser(name, email, password)` - POST /api/auths/signup
- `getSessionUser(token)` - GET /api/auths/
- `updateUserPassword(token, password, newPassword)` - POST /api/auths/update/password
- `getBackendConfig()` - GET /api/config (public endpoint, no auth)
- `generateAPIKey(token)` - POST /api/auths/api_key
- `deleteAPIKey(token, keyId)` - DELETE /api/auths/api_key/{id}

**Used by:**
- `routes/(app)/auth/+page.svelte` - Sign in/sign up forms
- `routes/(app)/+layout.svelte` - Session restoration on app load
- `lib/components/admin/Settings/Users.svelte` - User management

**Returns:**
- SessionUserResponse with token, user object, and permissions
- BackendConfig with version, features, OAuth providers

### users/index.ts
User management and settings API calls.

**Key Functions:**
- `getUsers(token)` - GET /api/users (admin only)
- `getUserById(token, userId)` - GET /api/users/{id}
- `updateUserById(token, userId, data)` - POST /api/users/{id}/update
- `deleteUserById(token, userId)` - DELETE /api/users/{id}
- `getUserSettings(token)` - GET /api/users/user/settings
- `updateUserSettings(token, settings)` - POST /api/users/user/settings/update
- `getUserPermissions(token)` - GET /api/users/permissions

**Used by:**
- `lib/components/admin/Settings/Users.svelte` - User list and management
- `lib/components/workspace/Settings.svelte` - User preferences
- `routes/(app)/+layout.svelte` - Loads settings on mount

**Updates Stores:**
- `settings` store after getUserSettings()
- `user` store after updateUserById()

### chats/index.ts
Chat history and message management API calls.

**Key Functions:**
- `createNewChat(token, chat)` - POST /api/chats/new
- `getChatList(token, page?)` - GET /api/chats/list (paginated)
- `getChatById(token, id)` - GET /api/chats/{id}
- `getChatByShareId(token, shareId)` - GET /api/chats/share/{id}
- `updateChatById(token, id, chat)` - POST /api/chats/{id}
- `deleteChatById(token, id)` - DELETE /api/chats/{id}
- `getArchivedChatList(token)` - GET /api/chats/archived
- `getAllChats(token)` - GET /api/chats/all
- `searchChatByName(token, name)` - GET /api/chats/search?name={name}
- `archiveChatById(token, id)` - GET /api/chats/{id}/archive
- `shareChatById(token, id)` - POST /api/chats/{id}/share
- `cloneChatById(token, id)` - GET /api/chats/{id}/clone
- `getTagsById(token, id)` - GET /api/chats/{id}/tags
- `addTagById(token, id, tagName)` - POST /api/chats/{id}/tags
- `deleteTagById(token, id, tagName)` - DELETE /api/chats/{id}/tags

**Used by:**
- `lib/components/chat/Sidebar.svelte` - Chat list display
- `lib/components/chat/MessageInput.svelte` - New chat creation
- `routes/(app)/c/[id]/+page.svelte` - Load chat on route mount

**Updates Stores:**
- `chats` store via setChatHistory()
- `chatId`, `chatTitle` stores for current chat

### models/index.ts
LLM model management API calls.

**Key Functions:**
- `getModels(token)` - GET /api/models
- `getModelById(token, id)` - GET /api/models/{id}
- `createNewModel(token, model)` - POST /api/models/create
- `updateModelById(token, id, model)` - POST /api/models/{id}/update
- `deleteModelById(token, id)` - DELETE /api/models/{id}
- `toggleModelById(token, id)` - POST /api/models/id/{id}/toggle
- `getModelValves(token, id)` - GET /api/models/{id}/valves
- `updateModelValves(token, id, valves)` - POST /api/models/{id}/valves/update

**Used by:**
- `routes/(app)/+layout.svelte` - Loads models on app mount
- `lib/components/chat/ModelSelector.svelte` - Model dropdown
- `lib/components/admin/Settings/Models.svelte` - Model management

**Updates Stores:**
- `models` store with merged OpenAI + Ollama models

### files/index.ts
File upload, download, and management API calls.

**Key Functions:**
- `uploadFile(token, file)` - POST /api/files (multipart/form-data)
- `getFileById(token, id)` - GET /api/files/{id}
- `getFileContentById(token, id)` - GET /api/files/{id}/content (download)
- `updateFileById(token, id, data)` - POST /api/files/{id}/update
- `deleteFileById(token, id)` - DELETE /api/files/{id}
- `getFileDataContent(token, fileId)` - GET /api/files/{id}/data/content

**Used by:**
- `lib/components/chat/MessageInput.svelte` - File attachment upload
- `lib/components/workspace/Files.svelte` - File browser
- `lib/components/common/FileDrop.svelte` - Drag & drop uploads

**File Processing Flow:**
```
uploadFile() → Backend processes file
  ↓
Backend calls retrieval.process_file()
  ↓
File embedded in vector DB
  ↓
Frontend calls getFileById() for metadata
```

### retrieval/index.ts
RAG (Retrieval-Augmented Generation) API calls.

**Key Functions:**
- `processFile(token, fileId, collectionName, content?)` - POST /api/retrieval/process/file
- `queryDoc(token, collectionName, query, k?)` - POST /api/retrieval/query/doc
- `queryCollection(token, collectionNames, query, k?)` - POST /api/retrieval/query/collection
- `getRAGConfig(token)` - GET /api/retrieval/config
- `updateRAGConfig(token, config)` - POST /api/retrieval/config/update
- `scanDocs(token)` - POST /api/retrieval/scan
- `resetVectorDB(token)` - POST /api/retrieval/reset
- `getWebSearchConfig(token)` - GET /api/retrieval/web/config
- `updateWebSearchConfig(token, config)` - POST /api/retrieval/web/config/update
- `searchWeb(token, query)` - POST /api/retrieval/web/search

**Used by:**
- `lib/components/workspace/Knowledge.svelte` - Document processing UI
- `lib/components/admin/Settings/Documents.svelte` - RAG configuration
- `lib/components/chat/MessageInput.svelte` - File context handling

**RAG Workflow:**
```
File uploaded via files/index.ts
  ↓
processFile() chunks + embeds document
  ↓
queryDoc() retrieves relevant chunks
  ↓
Chunks passed to LLM in system prompt
```

### knowledge/index.ts
Knowledge base management API calls.

**Key Functions:**
- `createNewKnowledge(token, data)` - POST /api/knowledge
- `getKnowledgeBases(token)` - GET /api/knowledge
- `getKnowledgeById(token, id)` - GET /api/knowledge/{id}
- `updateKnowledgeById(token, id, data)` - POST /api/knowledge/{id}/update
- `deleteKnowledgeById(token, id)` - DELETE /api/knowledge/{id}
- `addFileToKnowledge(token, knowledgeId, fileId)` - POST /api/knowledge/{id}/file/add
- `removeFileFromKnowledge(token, knowledgeId, fileId)` - POST /api/knowledge/{id}/file/remove
- `resetKnowledgeById(token, id)` - POST /api/knowledge/{id}/reset

**Used by:**
- `lib/components/workspace/Knowledge.svelte` - Knowledge base browser
- `lib/components/admin/Settings/Knowledge.svelte` - KB management
- `lib/components/chat/MessageInput.svelte` - Knowledge selection

**Updates Stores:**
- `knowledge` store with list of knowledge bases

### tools/index.ts & functions/index.ts
Tool and function management API calls (Open WebUI plugin system).

**Key Functions (tools):**
- `getTools(token)` - GET /api/tools
- `getToolById(token, id)` - GET /api/tools/{id}
- `exportToolById(token, id)` - GET /api/tools/{id}/export
- `createNewTool(token, data)` - POST /api/tools/create
- `updateToolById(token, id, data)` - POST /api/tools/{id}/update
- `deleteToolById(token, id)` - DELETE /api/tools/{id}
- `getToolValves(token, id)` - GET /api/tools/{id}/valves
- `updateToolValves(token, id, valves)` - POST /api/tools/{id}/valves/update
- `getToolUserValves(token, id)` - GET /api/tools/{id}/valves/user
- `updateToolUserValves(token, id, valves)` - POST /api/tools/{id}/valves/user/update

**Used by:**
- `routes/(app)/+layout.svelte` - Loads tools on app mount
- `lib/components/workspace/Tools.svelte` - Tool browser
- `lib/components/admin/Settings/Tools.svelte` - Tool management

**Updates Stores:**
- `tools` store with available tools
- `functions` store with available functions

### prompts/index.ts
Prompt template management API calls.

**Key Functions:**
- `createNewPrompt(token, data)` - POST /api/prompts/create
- `getPrompts(token)` - GET /api/prompts
- `getPromptByCommand(token, command)` - GET /api/prompts/command/{command}
- `updatePromptByCommand(token, command, data)` - POST /api/prompts/command/{command}/update
- `deletePromptByCommand(token, command)` - DELETE /api/prompts/command/{command}

**Used by:**
- `lib/components/chat/MessageInput.svelte` - Slash command suggestions
- `lib/components/workspace/Prompts.svelte` - Prompt management

**Updates Stores:**
- `prompts` store with slash command templates

### memories/index.ts
User memory (long-term context) API calls.

**Key Functions:**
- `addMemory(token, memory)` - POST /api/memories/add
- `getMemories(token)` - GET /api/memories
- `getMemoryById(token, id)` - GET /api/memories/{id}
- `updateMemoryById(token, id, memory)` - POST /api/memories/{id}/update
- `deleteMemoryById(token, id)` - DELETE /api/memories/{id}
- `resetMemories(token)` - POST /api/memories/reset

**Used by:**
- `lib/components/workspace/Memories.svelte` - Memory browser
- `utils/middleware.py` on backend - Injects memories into LLM context

### channels/index.ts
Collaborative channels API calls.

**Key Functions:**
- `createNewChannel(token, data)` - POST /api/channels/create
- `getChannels(token)` - GET /api/channels
- `getChannelById(token, id)` - GET /api/channels/{id}
- `updateChannelById(token, id, data)` - POST /api/channels/{id}/update
- `deleteChannelById(token, id)` - DELETE /api/channels/{id}
- `getChannelMessages(token, id)` - GET /api/channels/{id}/messages
- `postChannelMessage(token, id, message)` - POST /api/channels/{id}/messages

**Used by:**
- `lib/components/workspace/Channels.svelte` - Channel list
- `routes/(app)/channels/[id]/+page.svelte` - Channel view

**WebSocket Integration:**
- Creates messages via HTTP
- Real-time updates via socket 'channel-events'

### ollama/index.ts & openai/index.ts
LLM backend proxy API calls.

**Key Functions (ollama):**
- `getOllamaModels(base_url, token)` - GET {base_url}/api/tags
- `generateOllamaCompletion(token, payload)` - POST /ollama/api/generate
- `generateOllamaChatCompletion(token, payload)` - POST /ollama/api/chat
- `generateOllamaEmbeddings(token, payload)` - POST /ollama/api/embeddings

**Key Functions (openai):**
- `getOpenAIModels(token, url?)` - GET /openai/api/models
- `generateOpenAIChatCompletion(token, payload, url?)` - POST /openai/api/chat/completions

**Used by:**
- `lib/components/chat/Messages.svelte` - Chat completions
- `routes/(app)/+layout.svelte` - Model fetching
- `utils/middleware.py` on backend - Proxies to actual LLM services

**Streaming Pattern:**
```javascript
const stream = await generateOpenAIChatCompletion(token, payload);
for await (const chunk of stream) {
  // Process SSE chunks
}
```

### audio/index.ts
Speech-to-text and text-to-speech API calls.

**Key Functions:**
- `transcribeAudio(token, file)` - POST /api/audio/transcriptions
- `synthesizeSpeech(token, speaker, text)` - POST /api/audio/speech

**Used by:**
- `lib/components/chat/MessageInput.svelte` - Voice input
- `lib/components/chat/Messages.svelte` - Read aloud feature

### images/index.ts
Image generation API calls.

**Key Functions:**
- `generateImage(token, prompt, model, size?, n?)` - POST /api/images/generations

**Used by:**
- `lib/components/chat/MessageInput.svelte` - Image generation command
- `lib/components/workspace/ImageGenerator.svelte`

## Architecture & Patterns

### Authentication Pattern
All API calls follow consistent auth header injection:
```typescript
const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};
```

Token sourced from:
- `localStorage.token` (primary)
- Function parameter `token` passed from components

### Error Handling Pattern
```typescript
try {
  const res = await fetch(url, { method, headers, body });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return await res.json();
} catch (error) {
  console.error(error);
  throw error;
}
```

Components catch errors and display via toast notifications.

### Streaming Response Pattern
For chat completions and SSE endpoints:
```typescript
const response = await fetch(url, options);
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // Parse SSE or JSON chunks
}
```

### Form Data Upload Pattern
For file uploads:
```typescript
const formData = new FormData();
formData.append('file', file);

await fetch('/api/files', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
```

### URL Construction Pattern
Base URLs configured via environment:
```typescript
const WEBUI_API_BASE_URL = dev ? '' : env.PUBLIC_API_BASE_URL;
const url = `${WEBUI_API_BASE_URL}/api/chats/${id}`;
```

## Integration Points

### Frontend Components → APIs
All UI interactions route through API layer:
```
User clicks button
  ↓
Component calls API function (e.g., deleteChat())
  ↓
API makes authenticated HTTP request
  ↓
Backend processes request
  ↓
API returns parsed response
  ↓
Component updates store or local state
```

### APIs → Backend Routers
Direct 1:1 mapping to FastAPI endpoints:
- `chats/index.ts` → `backend/routers/chats.py`
- `users/index.ts` → `backend/routers/auths.py` + `users.py`
- `retrieval/index.ts` → `backend/routers/retrieval.py`
- `models/index.ts` → `backend/routers/models.py`
- `knowledge/index.ts` → `backend/routers/knowledge.py`
- `tools/index.ts` → `backend/routers/tools.py`

### APIs → Stores
API calls populate Svelte stores:
```typescript
// In routes/(app)/+layout.svelte
onMount(async () => {
  const token = localStorage.token;

  models.set(await getModels(token));
  chats.set(await getChatList(token));
  tools.set(await getTools(token));
  knowledge.set(await getKnowledgeBases(token));
  // ... etc
});
```

### WebSocket Coordination
HTTP APIs create resources; WebSocket broadcasts updates:
```
POST /api/chats/new (via createNewChat())
  ↓
Backend creates chat in database
  ↓
Backend emits 'chat-events' via socket
  ↓
Frontend socket listener updates chats store
  ↓
All open tabs see new chat
```

## Key Workflows

### Authentication Flow
```
User submits login form
  ↓
signinUser(email, password)
  ↓
POST /api/auths/signin
  ↓
Backend validates credentials
  ↓
Returns { token, user }
  ↓
localStorage.token = token
  ↓
user.set(userData)
  ↓
Navigate to /
  ↓
App layout calls getSessionUser(token)
  ↓
Loads all stores via API calls
```

### Chat Creation Flow
```
User types message
  ↓
createNewChat(token, { messages, ... })
  ↓
POST /api/chats/new
  ↓
Backend creates chat record
  ↓
Returns chat object
  ↓
chats.update(c => [newChat, ...c])
  ↓
Navigate to /c/{chat.id}
  ↓
Route loads via getChatById()
```

### File Upload + RAG Flow
```
User drops file
  ↓
uploadFile(token, file)
  ↓
POST /api/files (multipart)
  ↓
Backend saves file to storage
  ↓
processFile(token, fileId, collectionName)
  ↓
POST /api/retrieval/process/file
  ↓
Backend chunks + embeds document
  ↓
Returns file metadata
  ↓
User enables file in chat
  ↓
Chat completion includes file context via queryDoc()
```

### Knowledge Base Query Flow
```
User selects knowledge base
  ↓
getKnowledgeById(token, id)
  ↓
GET /api/knowledge/{id}
  ↓
Returns { files: [...] }
  ↓
User sends message
  ↓
queryCollection(token, [knowledgeId], query)
  ↓
POST /api/retrieval/query/collection
  ↓
Backend searches vector DB
  ↓
Returns top-k documents
  ↓
Documents injected into LLM context
```

### Model Selection Flow
```
App loads
  ↓
getModels(token)
  ↓
GET /api/models
  ↓
Backend merges OpenAI + Ollama models
  ↓
Returns unified model list
  ↓
models.set(data)
  ↓
ModelSelector component subscribes via $models
  ↓
User selects model
  ↓
selectedModels store updated
  ↓
Next chat uses selected model
```

## Important Notes

### Critical Dependencies
- All API calls require valid JWT token from localStorage
- Token expiration triggers redirect to /auth
- CORS handled by backend (CORS middleware configured)
- BASE_URL configured via PUBLIC_API_BASE_URL environment variable

### Error Handling Patterns
- Network errors: Components display toast notifications
- 401 Unauthorized: Triggers logout and redirect to /auth
- 403 Forbidden: Permission error toast
- 500 Server Error: Generic error toast with backend message

### Performance Considerations
- API calls are async; components show loading states
- Large lists (chats, models) fetched once on app mount, cached in stores
- Pagination used for chat history (getChatList supports page parameter)
- File uploads support progress tracking via FormData events
- Streaming used for chat completions to reduce perceived latency

### Type Safety
- All functions typed with TypeScript
- Request/response types defined in adjacent `.d.ts` files
- Pydantic models on backend enforce schema validation
- Runtime validation via JSON schema in some endpoints

### Security
- Tokens stored in localStorage (vulnerable to XSS)
- No refresh token mechanism (long-lived JWTs)
- API keys managed separately via generateAPIKey()
- File uploads validated by backend (extension whitelist, size limits)
- CSRF protection not implemented (stateless JWT auth)

### Caching Strategy
- No HTTP-level caching (Cache-Control headers not used)
- Store-based caching: API calls populate stores, components read from stores
- Manual cache invalidation via store.set() after mutations
- Real-time updates via WebSocket keep stores synchronized

### Development Patterns
- Use `dev` from `$app/environment` to toggle dev/prod URLs
- Environment variables via `import { env } from '$env/dynamic/public'`
- API functions exported individually for tree-shaking
- Consistent naming: `get*`, `create*`, `update*`, `delete*`
