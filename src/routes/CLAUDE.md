# Frontend Routes Directory

This directory implements SvelteKit's file-based routing system for Open WebUI. Routes define the application's URL structure, handle navigation, implement route guards for authentication/authorization, and orchestrate initial data loading via page load functions.

## Directory Structure

### (app)/ - Authenticated Application Routes
Route group with shared layout requiring authentication.

**+layout.svelte:**
- Root application layout wrapper
- **Critical Initialization Point** - Loads ALL stores on mount:
  - `getSessionUser()` → `user` store
  - `getModels()` → `models` store
  - `getTools()` → `tools` store
  - `getKnowledgeBases()` → `knowledge` store
  - `getPrompts()` → `prompts` store
  - `getUserSettings()` → `settings` store
  - Socket.IO connection initialization
- Renders `<Navbar />`, `<Sidebar />`, main content slot, `<Footer />`
- Route guard: Redirects to `/auth` if `!localStorage.token`

**+page.svelte (/):**
- Main chat interface (default route)
- Renders `<Messages />`, `<MessageInput />`, `<ModelSelector />`
- Creates new chat on mount if `!$chatId`
- Loads chat history via `getChatList()`

**Used by:**
- All authenticated routes (inherit layout)

**Uses:**
- `$lib/apis/` - All API modules for initial data load
- `$lib/components/layout/` - Navbar, Sidebar, Footer
- `$lib/components/chat/` - Chat interface components
- `$lib/stores` - All global stores

### (app)/c/[id]/ - Individual Chat Routes
Dynamic route for specific chat conversations.

**+page.svelte:**
- Loads chat by ID from URL parameter
- `onMount()`: `getChatById(localStorage.token, id)` → `chatId`, `chatTitle` stores
- Renders same interface as root `/` but with specific chat loaded
- Handles chat not found (404 redirect)

**Used by:**
- `<Sidebar />` navigation links (`/c/{chat.id}`)
- Share links (after user accepts share)

**Uses:**
- `$lib/apis/chats/index.ts` - getChatById()
- `$lib/components/chat/Messages.svelte` - Message display

**Route Parameters:**
- `id` - Chat UUID from database

### (app)/admin/ - Admin Panel Routes
Protected routes for administrators.

**+page.svelte:**
- Admin dashboard overview
- User statistics, system metrics
- Quick actions (create user, manage models)

**+layout.svelte:**
- Admin-specific layout with sidebar navigation
- Route guard: `if ($user?.role !== 'admin') goto('/')`

**admin/settings/+page.svelte:**
- Admin settings interface
- Tabs for different setting categories
- Renders `<admin/Settings/General>`, `<admin/Settings/Users>`, etc.

**Used by:**
- Admin users only (role='admin')

**Uses:**
- `$lib/components/admin/` - All admin components
- `$lib/apis/auths/index.ts` - getAdminConfig(), updateAdminConfig()
- `$lib/apis/users/index.ts` - getUsers()
- `$lib/stores` - user, config stores

**Access Control:**
- Route-level guard checks `$user.role === 'admin'`
- Individual components check permissions
- Redirects non-admins to `/`

### (app)/workspace/ - User Workspace Routes
Resource management interface for authenticated users.

**+layout.svelte:**
- Workspace layout with navigation tabs
- Tabs: Files, Knowledge, Tools, Prompts, Models, Memories

**workspace/files/+page.svelte:**
- File browser and upload interface
- Renders `<workspace/Files>`

**workspace/knowledge/+page.svelte:**
- Knowledge base management
- Renders `<workspace/Knowledge>`

**workspace/tools/+page.svelte:**
- Tool browser and configuration
- Renders `<workspace/Tools>`

**workspace/prompts/+page.svelte:**
- Prompt template editor
- Renders `<workspace/Prompts>`

**workspace/models/+page.svelte:**
- Model preferences and history
- Renders `<workspace/Models>`

**workspace/memories/+page.svelte:**
- Long-term memory viewer
- Renders `<workspace/Memories>`

**workspace/settings/+page.svelte:**
- User-specific settings (not admin)
- Profile, preferences, API keys

**Used by:**
- All authenticated users
- Accessed via workspace navigation menu

**Uses:**
- `$lib/components/workspace/` - All workspace components
- `$lib/apis/` - files, knowledge, tools, prompts, memories
- `$lib/stores` - knowledge, tools, prompts, files, settings

### (app)/channels/[id]/ - Channel Routes
Collaborative channel interface.

**+page.svelte:**
- Channel conversation view
- Real-time message updates via WebSocket
- Renders channel messages and input

**Used by:**
- Users with channel access
- Channel list in workspace

**Uses:**
- `$lib/apis/channels/index.ts` - getChannelById(), getChannelMessages()
- `$lib/components/workspace/Channels.svelte` - Channel UI
- `$lib/stores` - socket, channels, user

**WebSocket Integration:**
- Subscribes to `channel:{id}` room on mount
- Receives real-time messages via socket 'channel-events'
- Typing indicators via socket awareness

### auth/ - Authentication Routes
Public routes for sign in/sign up (no authentication required).

**auth/+page.svelte:**
- Login/signup form toggle
- Email/password authentication
- OAuth provider buttons (if configured)
- Renders sign in form by default

**Used by:**
- Unauthenticated users
- Redirected from protected routes

**Uses:**
- `$lib/apis/auths/index.ts` - signinUser(), signupUser()
- `$lib/components/auth/` - Login forms, OAuth buttons

**Flow:**
```
User submits credentials
  ↓
signinUser(email, password)
  ↓
Receives { token, user }
  ↓
localStorage.token = token
  ↓
user.set(userData)
  ↓
goto('/') - Redirect to main app
  ↓
(app)/+layout.svelte initializes stores
```

**Route Guard:**
- Redirects to `/` if already authenticated (`localStorage.token`)

### s/[id]/ - Public Shared Chat Routes
Public routes for shared chat links (no authentication required).

**+page.svelte:**
- Displays shared chat in read-only mode
- No sidebar, no navigation
- `getChatByShareId(shareId)`

**Used by:**
- Public share links (e.g., https://app.com/s/abc123)
- Users without accounts

**Uses:**
- `$lib/apis/chats/index.ts` - getChatByShareId()
- `$lib/components/chat/Messages.svelte` - Read-only message display

**Access Control:**
- No authentication required
- Share ID must be valid (backend checks)
- Cannot modify or send new messages

## Architecture & Patterns

### SvelteKit File-Based Routing
```
routes/
  (app)/
    +layout.svelte        → Shared layout for all /routes
    +page.svelte          → / (root)
    c/
      [id]/
        +page.svelte      → /c/[id]
    admin/
      +layout.svelte      → Shared layout for /admin/*
      +page.svelte        → /admin
      settings/
        +page.svelte      → /admin/settings
```

### Route Hierarchy & Layouts
```
app/+layout.svelte (outermost)
  ↓
(app)/+layout.svelte (authenticated wrapper)
  ↓
(app)/admin/+layout.svelte (admin sidebar)
  ↓
(app)/admin/settings/+page.svelte (content)
```

Each layout wraps its children via `<slot />`.

### Route Guards Pattern
**Authentication Guard (in (app)/+layout.svelte):**
```svelte
<script>
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  onMount(() => {
    if (!localStorage.token) {
      goto('/auth');
      return;
    }

    // Initialize app...
  });
</script>
```

**Authorization Guard (in admin/+layout.svelte):**
```svelte
<script>
  import { user } from '$lib/stores';
  import { goto } from '$app/navigation';

  $: if ($user && $user.role !== 'admin') {
    goto('/');
  }
</script>
```

### Data Loading Pattern
**In +page.svelte onMount:**
```svelte
<script>
  import { onMount } from 'svelte';
  import { getChatById } from '$lib/apis/chats';
  import { chatId, chatTitle } from '$lib/stores';

  export let data; // From +page.ts load function (if used)

  onMount(async () => {
    const chat = await getChatById(localStorage.token, id);
    chatId.set(chat.id);
    chatTitle.set(chat.title);
  });
</script>
```

**Alternative: +page.ts load function (SSR-compatible):**
```typescript
// +page.ts
export async function load({ params, fetch }) {
  const chat = await getChatById(token, params.id);
  return { chat };
}
```

Note: Open WebUI uses SPA mode (`ssr: false`), so load functions execute client-side only.

### Navigation Patterns
**Programmatic Navigation:**
```svelte
<script>
  import { goto } from '$app/navigation';

  function navigateToChat(id) {
    goto(`/c/${id}`);
  }
</script>
```

**Declarative Navigation:**
```svelte
<a href="/c/{chat.id}">Open Chat</a>
```

SvelteKit intercepts `<a>` clicks for client-side navigation.

### Store Initialization Hierarchy
```
1. User visits / (or any (app) route)
2. (app)/+layout.svelte onMount executes
3. Check authentication (redirect if needed)
4. Load session user → user store
5. Load all resources:
   - getModels() → models store
   - getTools() → tools store
   - getKnowledgeBases() → knowledge store
   - getUserSettings() → settings store
   - getChatList() → chats store
6. Initialize socket connection
7. Render child routes with populated stores
```

All child routes depend on this initialization.

## Integration Points

### Routes → API Layer
Routes orchestrate API calls on mount:
```
Route loads
  ↓
onMount() async function
  ↓
API calls (getChatById, getModels, etc.)
  ↓
Populate stores
  ↓
Components subscribe to stores
  ↓
UI renders with data
```

### Routes → Stores
Routes update stores based on route parameters:
```
User navigates to /c/abc-123
  ↓
Route extracts id from URL params
  ↓
getChatById('abc-123')
  ↓
chatId.set('abc-123')
  ↓
All components reading $chatId update
```

### Routes → Components
Routes render components via imports:
```svelte
<!-- routes/(app)/+page.svelte -->
<script>
  import Messages from '$lib/components/chat/Messages.svelte';
  import MessageInput from '$lib/components/chat/MessageInput.svelte';
</script>

<Messages />
<MessageInput />
```

### Routes → WebSocket
Layout establishes socket connection:
```svelte
<!-- (app)/+layout.svelte -->
<script>
  import { socket } from '$lib/stores';
  import io from 'socket.io-client';

  onMount(() => {
    const socketInstance = io('/ws/socket.io', {
      auth: { token: localStorage.token }
    });

    socket.set(socketInstance);

    socketInstance.on('chat-events', handleChatEvent);
  });
</script>
```

Child routes and components access via `$socket` store.

### Routes → Browser APIs
Routes interact with browser features:
```svelte
<script>
  import { onMount } from 'svelte';

  onMount(() => {
    // localStorage
    const token = localStorage.token;

    // sessionStorage
    const draft = sessionStorage.getItem('chat-draft');

    // URL params
    const params = new URLSearchParams(window.location.search);

    // History API (via SvelteKit)
    goto('/new-route', { replaceState: true });
  });
</script>
```

## Key Workflows

### Initial App Load Workflow
```
1. User visits https://app.com/
2. Browser loads index.html
3. SvelteKit client-side router initializes
4. Routes to routes/(app)/+page.svelte
5. (app)/+layout.svelte onMount executes:
   a. Check localStorage.token
   b. If missing → goto('/auth')
   c. If present → getSessionUser()
   d. Load all stores in parallel
   e. Initialize socket connection
6. +page.svelte renders chat interface
7. Components subscribe to populated stores
8. UI displays with user data
```

### Chat Navigation Workflow
```
User clicks chat in sidebar
  ↓
<a href="/c/{chat.id}"> clicked
  ↓
SvelteKit intercepts, client-side navigation
  ↓
Routes to (app)/c/[id]/+page.svelte
  ↓
Route extracts id from params
  ↓
onMount: getChatById(token, id)
  ↓
Update chatId, chatTitle stores
  ↓
Messages component loads chat history
  ↓
URL updates to /c/{id}
  ↓
Browser history entry added
```

### Authentication Workflow
```
Unauthenticated user visits /
  ↓
(app)/+layout.svelte guard detects !localStorage.token
  ↓
goto('/auth')
  ↓
auth/+page.svelte renders login form
  ↓
User submits credentials
  ↓
signinUser(email, password)
  ↓
Backend returns { token, user }
  ↓
localStorage.token = token
  ↓
user.set(userData)
  ↓
goto('/')
  ↓
(app)/+layout.svelte initializes app
  ↓
User sees chat interface
```

### Admin Access Workflow
```
Admin clicks "Admin Panel" link
  ↓
goto('/admin')
  ↓
Routes to (app)/admin/+page.svelte
  ↓
admin/+layout.svelte checks $user.role
  ↓
If role !== 'admin' → goto('/')
  ↓
If admin → Render admin layout + sidebar
  ↓
Admin navigates to /admin/settings
  ↓
Renders settings page with tabs
  ↓
Admin modifies settings
  ↓
updateAdminConfig(token, config)
  ↓
config store updated
  ↓
Settings saved to backend
```

### Shared Chat Access Workflow
```
User receives link https://app.com/s/abc123
  ↓
Browser loads link (no auth required)
  ↓
Routes to s/[id]/+page.svelte
  ↓
Extract shareId from params
  ↓
getChatByShareId(shareId)
  ↓
Backend validates share ID
  ↓
Returns chat data (if valid)
  ↓
Render read-only chat view
  ↓
No sidebar, no message input
  ↓
User can view but not interact
```

### Workspace Navigation Workflow
```
User clicks "Workspace" in navbar
  ↓
goto('/workspace/files')
  ↓
Routes to (app)/workspace/+layout.svelte
  ↓
Renders workspace tabs (Files, Knowledge, etc.)
  ↓
Routes to workspace/files/+page.svelte
  ↓
Renders <workspace/Files> component
  ↓
Component calls getFiles() (if not in store)
  ↓
Displays file list
  ↓
User clicks "Knowledge" tab
  ↓
goto('/workspace/knowledge')
  ↓
Routes to workspace/knowledge/+page.svelte
  ↓
Renders <workspace/Knowledge>
```

## Important Notes

### Critical Dependencies
- All (app) routes require valid `localStorage.token`
- Stores must be initialized in (app)/+layout.svelte before child routes render
- Socket connection established once in root layout, shared across all routes
- Route guards must check authentication synchronously (onMount is too late)

### SvelteKit Configuration
- SPA mode: `ssr: false` in svelte.config.js
- No server-side rendering (client-side only)
- `+page.ts` load functions execute in browser
- No server endpoints (`+server.ts` not used)

### Performance Considerations
- Initial load fetches ALL stores (models, tools, knowledge, etc.) in parallel
- Large chat histories may slow route transitions (consider pagination)
- Socket reconnection on route change (not ideal; should persist)
- Store subscriptions cleaned up on route unmount (via Svelte's auto-unsubscribe)

### Navigation Behavior
- Client-side routing (no page reload)
- Browser back/forward buttons work correctly
- URL updates trigger route reactivity
- Programmatic navigation via `goto()`
- Link prefetching disabled by default (can enable via `data-sveltekit-prefetch`)

### Route Protection Patterns
- **Authentication**: Check `localStorage.token` in layout onMount
- **Authorization**: Check `$user.role` or `$user.permissions` in reactive blocks
- **Redirect Timing**: Use `onMount()` for async redirects, `$:` reactive blocks for synchronous
- **Fallback Routes**: No 404 page defined; unmatched routes show blank

### State Persistence
- Chat drafts: sessionStorage (per-tab)
- User preferences: localStorage + backend sync
- Authentication: localStorage.token
- Navigation state: SvelteKit history (browser-managed)

### Security Considerations
- No server-side route protection (API validates all requests)
- Token validation happens on each API call, not route level
- Admin routes protected client-side (not secure alone; backend validates)
- Public share routes require valid share ID (backend-enforced)
- XSS risk: Avoid `{@html}` except in controlled markdown rendering

### Testing Considerations
- Mock `goto()` from `$app/navigation` in tests
- Mock store values for route guards
- Test route guard redirects (auth required, admin required)
- Test dynamic route parameters ([id])
- Integration tests for full workflows (login → chat → navigate)

### Route Organization Best Practices
- Group related routes via `(group)` syntax
- Shared layouts reduce code duplication
- Route-specific logic in +page.svelte, shared logic in +layout.svelte
- Keep data fetching in routes, not components (easier to test)
- Use stores for cross-route state, local state for route-specific data
