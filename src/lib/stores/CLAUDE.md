# Frontend Stores Directory

This directory contains Svelte reactive stores that manage global application state for Open WebUI. Stores serve as the single source of truth for user sessions, configuration, UI state, and real-time data, bridging the backend API layer and frontend components.

## Files

### index.ts
Central store definitions file exporting 40+ Svelte writable stores.

**Backend/Session Stores:**
- `WEBUI_NAME` - Application name from backend config
- `config` - Global configuration (features, OAuth, version, default models)
- `user` - Current authenticated user (id, email, role, permissions, profile_image_url)

**Frontend UI State:**
- `mobile` - Responsive breakpoint indicator
- `socket` - Socket.io client instance for real-time communication
- `activeUserIds` - Currently active users (from socket)
- `theme` - User theme preference (system/light/dark)
- `showSidebar/Search/Settings/Shortcuts/ArchivedChats/Changelog/Controls/Overview/Artifacts/CallOverlay` - Modal visibility toggles

**Chat Session:**
- `chatId`, `chatTitle` - Current chat state
- `currentChatPage` - Pagination state
- `temporaryChatEnabled` - Incognito mode
- `scrollPaginationEnabled` - Infinite scroll toggle

**Data Collections:**
- `channels` - Collaboration channels
- `chats`, `pinnedChats` - Chat history
- `tags`, `selectedFolder` - Organization
- `models` - Available LLM models (OpenAI + Ollama union type)
- `prompts` - Slash command templates
- `knowledge` - Knowledge base documents for RAG
- `tools`, `functions`, `toolServers` - Extensibility
- `banners` - Admin message banners
- `settings` - User preferences (UI, audio, model params)

**Used by:**
- ALL Svelte components via `$storeName` auto-subscription syntax
- Routes for initialization and navigation guards
- API layer for token management

**Uses:**
- `$lib/constants` - APP_NAME, WEBUI_BASE_URL
- `$lib/types` - TypeScript interfaces (Banner, Model, Settings, etc.)
- `socket.io-client` - WebSocket connection
- `$lib/emoji-shortcodes.json` - Emoji data

## Architecture & Patterns

### Reactive Store Pattern
Svelte stores enable automatic UI updates:
```javascript
import { writable } from 'svelte/store';
export const user = writable(undefined);

// In components:
$: if ($user) {
    // Reactive block re-runs when user changes
}
```

### Initialization Flow
```
App starts → routes/(app)/+layout.svelte onMount
  ↓
Fetch session: getUserSettings(), getModels(), getTools(), etc.
  ↓
Populate stores: models.set(data), settings.set(data)
  ↓
Components subscribe via $models, $settings
  ↓
Automatic UI re-rendering on store changes
```

### Store Update Patterns
**Direct Set:**
```javascript
models.set(await getModels(token));
```

**Incremental Update:**
```javascript
chats.update(c => [...c, newChat]);
```

**Derived Stores (Computed):**
```javascript
import { derived } from 'svelte/store';
const isAdmin = derived(user, $user => $user?.role === 'admin');
```

### Socket Integration
```
Socket connection established in root layout
  ↓
socket.set(io('/ws/socket.io', { auth: { token }}))
  ↓
Event listeners attached:
  socket.on('chat-events', handleChatEvent)
  ↓
Store updates trigger component re-renders
```

## Integration Points

### Backend API → Stores
API calls populate stores on app mount:
```javascript
// In routes/(app)/+layout.svelte
onMount(async () => {
    config.set(await getBackendConfig());
    models.set(await getModels(token, directConnections));
    tools.set(await getTools(token));
    banners.set(await getBanners(token));
    // ... etc
});
```

### Stores → Components
Components consume via auto-subscription:
```svelte
<script>
    import { user, models, settings } from '$lib/stores';
</script>

{#if $user?.role === 'admin'}
    <AdminPanel />
{/if}

<select bind:value={selectedModel}>
    {#each $models as model}
        <option value={model.id}>{model.name}</option>
    {/each}
</select>
```

### Stores → WebSocket Events
Real-time updates flow through socket to stores:
```javascript
socket.on('chat-events', (data) => {
    if (data.type === 'chat:completion') {
        // Update chats store with new message
        chats.update(c => updateChatInList(c, data));
    }
});
```

## Key Workflows

### Authentication & Session
```
User signs in → POST /api/auths/signin
  ↓
Backend returns token + user object
  ↓
localStorage.token = token
user.set(userData)
  ↓
Socket connects with token
  ↓
App layout fetches and populates all stores
```

### Chat Management
```
User creates chat → POST /api/chats
  ↓
Backend returns chat object
  ↓
chats.update(c => [newChat, ...c])
  ↓
Components subscribed to $chats re-render
  ↓
Sidebar shows new chat in list
```

### Model Selection
```
User selects model in UI
  ↓
selectedModels store updated
  ↓
$: Reactive block detects change
  ↓
Tools auto-configured based on model.info.meta.toolIds
  ↓
UI updates tool selection
```

### Settings Persistence
```
User changes setting in UI
  ↓
settings.update(s => ({ ...s, newValue }))
  ↓
Component calls updateUserSettings(token, $settings)
  ↓
Backend persists to database
  ↓
Settings.set(response) ensures sync
```

## Important Notes

**Critical Dependencies:**
- All stores depend on initial data load in `(app)/+layout.svelte`
- `localStorage.token` must exist for API calls
- Socket connection required for real-time features
- Store subscriptions must be unsubscribed in `onDestroy` to prevent memory leaks

**Store Lifecycle:**
- Stores persist across navigation (SvelteKit SPA mode)
- Page reload resets stores (refetch from backend)
- sessionStorage used for temporary chat input state
- No persistence layer beyond localStorage for token

**Type Safety:**
- All stores typed via TypeScript generics `Writable<T>`
- Union types for models (OpenAIModel | OllamaModel)
- Optional chaining for nested access (`$user?.permissions?.workspace?.models`)

**Performance:**
- Stores trigger reactive updates; minimize unnecessary sets
- Derived stores recompute only when dependencies change
- Large arrays (chats, models) should use update() not set() for partial changes

**Security:**
- Token stored in localStorage (vulnerable to XSS)
- User permissions stored client-side (must validate server-side)
- Settings can be manipulated; backend validates on save
