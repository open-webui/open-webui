# Frontend Components Directory

This directory contains all Svelte UI components for Open WebUI, organized by feature domain. Components implement the visual interface, user interactions, and connect the API layer with Svelte stores, following a presentational/container component pattern with reactive state management.

## Directory Structure

### admin/
Admin panel components for system configuration and management.

**Key Components:**
- `Settings/` - Admin configuration panels
  - `General.svelte` - WEBUI_NAME, default models, JWT expiration
  - `Users.svelte` - User list, role management, creation/deletion
  - `Models.svelte` - Model management, toggle enable/disable
  - `Tools.svelte` - Tool registration, valve configuration
  - `Documents.svelte` - RAG settings, embedding models, chunk size
  - `Database.svelte` - Export/import, chat history management
  - `Connections.svelte` - OpenAI/Ollama endpoint configuration
  - `Audio.svelte` - TTS/STT engine selection
  - `Images.svelte` - Image generation settings
  - `Banners.svelte` - Site-wide announcement management
- `Knowledge/` - Knowledge base admin interface
- `Channels/` - Channel moderation interface

**Used by:**
- `routes/(app)/admin/+page.svelte` - Admin dashboard route
- `routes/(app)/admin/settings/+page.svelte` - Settings route

**Uses:**
- `$lib/apis/users/index.ts` - getUsers(), updateUserById(), deleteUserById()
- `$lib/apis/models/index.ts` - getModels(), toggleModelById()
- `$lib/apis/auths/index.ts` - getAdminConfig(), updateAdminConfig()
- `$lib/apis/retrieval/index.ts` - getRAGConfig(), updateRAGConfig()
- `$lib/stores` - config, user, models stores

**Access Control:**
- Requires `user.role === 'admin'`
- Route guards in `+page.svelte` redirect non-admins

### chat/
Core chat interface components.

**Key Components:**
- `Messages.svelte` - Message list with virtualization, streaming updates, regeneration
- `MessageInput.svelte` - Text input, file attachments, voice input, slash commands
- `Message/` - Individual message rendering
  - `Content.svelte` - Markdown rendering, code highlighting, LaTeX
  - `CodeBlock.svelte` - Syntax highlighting with copy button
  - `ResponseMessage.svelte` - LLM response with citations, sources
  - `UserMessage.svelte` - User message with edit capability
- `ModelSelector.svelte` - Model dropdown with search, favorites
- `Sidebar.svelte` - Chat history list with search, tags, folders
- `ShareChatModal.svelte` - Public chat link generation
- `Controls.svelte` - Temperature, top_p, max_tokens sliders
- `Artifacts.svelte` - Interactive code execution viewer

**Used by:**
- `routes/(app)/+page.svelte` - Main chat route
- `routes/(app)/c/[id]/+page.svelte` - Specific chat route

**Uses:**
- `$lib/apis/chats/index.ts` - getChatById(), updateChatById(), createNewChat()
- `$lib/apis/openai/index.ts` - generateOpenAIChatCompletion()
- `$lib/apis/ollama/index.ts` - generateOllamaChatCompletion()
- `$lib/apis/files/index.ts` - uploadFile()
- `$lib/apis/audio/index.ts` - transcribeAudio(), synthesizeSpeech()
- `$lib/stores` - chatId, chatTitle, models, settings, selectedModels

**WebSocket Integration:**
- Subscribes to `$socket` 'chat-events' for streaming updates
- Displays delta tokens in real-time
- Updates message state on completion

**Key Patterns:**
- Auto-scroll to bottom on new messages
- Virtualized rendering for long chat histories
- Debounced auto-save for draft messages
- Markdown + syntax highlighting via `svelte-markdown` + `highlight.js`

### workspace/
User workspace views for managing resources.

**Key Components:**
- `Files.svelte` - File browser with upload, delete, preview
- `Knowledge.svelte` - Knowledge base management interface
- `Tools.svelte` - Tool browser and configuration
- `Prompts.svelte` - Prompt template editor
- `Models.svelte` - User's model preferences and history
- `Memories.svelte` - Long-term memory viewer
- `Channels.svelte` - Channel list and creation
- `Settings.svelte` - User preferences (not admin settings)
- `Playground.svelte` - Model testing interface

**Used by:**
- `routes/(app)/workspace/+layout.svelte` - Workspace layout wrapper
- `routes/(app)/workspace/[section]/+page.svelte` - Dynamic section routes

**Uses:**
- `$lib/apis/files/index.ts` - uploadFile(), deleteFileById(), getFileContentById()
- `$lib/apis/knowledge/index.ts` - getKnowledgeBases(), addFileToKnowledge()
- `$lib/apis/tools/index.ts` - getTools(), updateToolUserValves()
- `$lib/apis/prompts/index.ts` - getPrompts(), createNewPrompt()
- `$lib/apis/memories/index.ts` - getMemories(), addMemory()
- `$lib/stores` - knowledge, tools, prompts, files

**Access Control:**
- Some sections require specific permissions
- Workspace settings respect user.permissions object

### common/
Reusable UI components shared across features.

**Key Components:**
- `Modal.svelte` - Base modal wrapper with backdrop, close button
- `ConfirmDialog.svelte` - Confirmation prompt for destructive actions
- `Toast.svelte` - Notification system (success, error, warning)
- `Tooltip.svelte` - Hover tooltip with positioning
- `Dropdown.svelte` - Generic dropdown menu component
- `Spinner.svelte` - Loading spinner
- `FileDropZone.svelte` - Drag & drop file upload area
- `CopyButton.svelte` - Copy-to-clipboard with feedback
- `SearchBar.svelte` - Search input with clear button
- `Pagination.svelte` - Page navigation controls
- `Badge.svelte` - Status badges (admin, pending, etc.)
- `UserAvatar.svelte` - Profile picture with fallback initials
- `MarkdownRenderer.svelte` - Markdown to HTML conversion

**Used by:**
- ALL feature components (admin, chat, workspace)

**Uses:**
- Minimal dependencies, mostly vanilla Svelte
- `svelte-markdown` for MarkdownRenderer
- `clipboard` API for CopyButton
- Svelte transitions for animations

**Key Patterns:**
- Slot-based composition for flexibility
- Event forwarding for parent handling
- CSS custom properties for theming
- Accessibility attributes (aria-*, role)

### layout/
Application shell and navigation components.

**Key Components:**
- `Navbar.svelte` - Top navigation bar with user menu, settings
- `Sidebar.svelte` - Main sidebar with navigation links (reused by chat sidebar)
- `Footer.svelte` - Footer with version, links
- `ThemeToggle.svelte` - Light/dark/system theme switcher
- `LanguageSelector.svelte` - i18n language selection
- `NotificationBell.svelte` - Notification center icon
- `QuickSettings.svelte` - Quick access settings panel

**Used by:**
- `routes/(app)/+layout.svelte` - App layout wrapper

**Uses:**
- `$lib/stores` - theme, user, config, showSidebar, showSettings
- `$lib/apis/auths/index.ts` - Logout functionality

**Responsive Behavior:**
- Mobile breakpoint detection via `$mobile` store
- Sidebar collapses to hamburger menu
- Touch-friendly tap targets

### icons/
SVG icon components as Svelte components.

**Pattern:**
```svelte
<script>
  export let className = '';
</script>
<svg class={className} ...>
  <!-- SVG path -->
</svg>
```

**Used by:**
- All components requiring icons
- Importable as `import ChevronIcon from '$lib/icons/ChevronIcon.svelte'`

## Architecture & Patterns

### Reactive State Pattern
All components use Svelte's reactive syntax:
```svelte
<script>
  import { user, chats } from '$lib/stores';

  $: isAdmin = $user?.role === 'admin';
  $: filteredChats = $chats.filter(c => c.archived === false);
</script>

{#if isAdmin}
  <AdminPanel />
{/if}

{#each filteredChats as chat}
  <ChatItem {chat} />
{/each}
```

### Component Communication Patterns

**Parent → Child (Props):**
```svelte
<!-- Parent -->
<ChatMessage message={msg} user={$user} />

<!-- Child -->
<script>
  export let message;
  export let user;
</script>
```

**Child → Parent (Events):**
```svelte
<!-- Child -->
<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  function handleClick() {
    dispatch('delete', { id: chat.id });
  }
</script>
<button on:click={handleClick}>Delete</button>

<!-- Parent -->
<ChatItem on:delete={handleDelete} />
```

**Sibling → Sibling (Stores):**
```svelte
<!-- Component A -->
<script>
  import { selectedModel } from '$lib/stores';
  selectedModel.set('gpt-4');
</script>

<!-- Component B (auto-updates) -->
<script>
  import { selectedModel } from '$lib/stores';
</script>
<div>Current: {$selectedModel}</div>
```

### Modal Pattern
```svelte
<script>
  import { showSettings } from '$lib/stores';
</script>

{#if $showSettings}
  <Modal on:close={() => showSettings.set(false)}>
    <SettingsContent />
  </Modal>
{/if}
```

Modals controlled by boolean stores (showSettings, showSidebar, showSearch, etc.)

### Form Handling Pattern
```svelte
<script>
  import { updateUserSettings } from '$lib/apis/users';

  let settings = $settings; // Clone from store
  let loading = false;

  async function handleSubmit() {
    loading = true;
    try {
      const updated = await updateUserSettings(localStorage.token, settings);
      settings.set(updated); // Update store on success
      toast.success('Settings saved');
    } catch (error) {
      toast.error(error.message);
    } finally {
      loading = false;
    }
  }
</script>

<form on:submit|preventDefault={handleSubmit}>
  <input bind:value={settings.name} />
  <button type="submit" disabled={loading}>Save</button>
</form>
```

### Streaming Response Pattern
For chat completions:
```svelte
<script>
  let content = '';
  let done = false;

  async function streamCompletion() {
    const stream = await generateOpenAIChatCompletion(token, payload);

    for await (const chunk of stream) {
      if (chunk.choices[0]?.delta?.content) {
        content += chunk.choices[0].delta.content;
      }
      if (chunk.choices[0]?.finish_reason) {
        done = true;
      }
    }
  }
</script>

<div class="message">
  {content}
  {#if !done}<Spinner />{/if}
</div>
```

### File Upload Pattern
```svelte
<script>
  import { uploadFile } from '$lib/apis/files';

  let files = [];
  let uploading = false;

  async function handleDrop(event) {
    files = Array.from(event.dataTransfer.files);
    uploading = true;

    for (const file of files) {
      try {
        await uploadFile(localStorage.token, file);
      } catch (error) {
        toast.error(`Failed to upload ${file.name}`);
      }
    }

    uploading = false;
  }
</script>

<div on:drop|preventDefault={handleDrop} on:dragover|preventDefault>
  Drop files here
</div>
```

## Integration Points

### Components → Stores
Components read/write reactive stores:
```
User interacts with component
  ↓
Component updates store (chats.update(...))
  ↓
All subscribed components re-render
  ↓
UI synchronizes across tabs via localStorage + socket events
```

### Components → APIs
UI actions trigger API calls:
```
User clicks "Delete Chat" button
  ↓
Component calls deleteChatById(token, id)
  ↓
API makes DELETE /api/chats/{id}
  ↓
Backend deletes chat
  ↓
API resolves successfully
  ↓
Component updates chats store
  ↓
Chat removed from sidebar
```

### Components → WebSocket
Real-time updates flow through socket:
```
Backend emits 'chat-events' socket event
  ↓
Messages.svelte subscribes to $socket
  ↓
$socket.on('chat-events', handleEvent)
  ↓
Component updates local message state
  ↓
Streaming content appears in real-time
```

### Components → Routes
Navigation handled by SvelteKit:
```
User clicks chat in sidebar
  ↓
<a href="/c/{chat.id}"> triggers navigation
  ↓
SvelteKit loads routes/(app)/c/[id]/+page.svelte
  ↓
Route's onMount calls getChatById(id)
  ↓
Chat data populates chatId and chatTitle stores
  ↓
Messages component renders chat history
```

## Key Workflows

### Chat Message Send Flow
```
User types message in MessageInput
  ↓
User presses Enter
  ↓
MessageInput.svelte handleSubmit()
  ↓
createNewChat() or updateChatById()
  ↓
API: POST /api/chats/new
  ↓
Backend creates chat, emits socket event
  ↓
generateOpenAIChatCompletion() streams response
  ↓
Messages.svelte receives 'chat-events' via socket
  ↓
Content renders token-by-token
  ↓
On completion, chat saved to database
  ↓
Sidebar updates with new chat title
```

### File Upload + Attachment Flow
```
User drops file on FileDropZone
  ↓
FileDropZone emits 'upload' event
  ↓
MessageInput handles event
  ↓
uploadFile(token, file)
  ↓
API: POST /api/files (multipart)
  ↓
Backend processes file
  ↓
processFile() embeds document
  ↓
FileDropZone shows uploaded file chip
  ↓
User sends message with file attached
  ↓
Backend queries vector DB for context
  ↓
LLM receives file chunks in system prompt
```

### Model Selection Flow
```
User opens ModelSelector dropdown
  ↓
ModelSelector renders $models from store
  ↓
User clicks model
  ↓
selectedModels.update(m => [...m, model.id])
  ↓
Dropdown closes
  ↓
MessageInput uses $selectedModels for next request
  ↓
Chat completion sent to selected model
```

### Theme Toggle Flow
```
User clicks ThemeToggle
  ↓
theme.set('dark') or 'light' or 'system'
  ↓
Store update triggers reactive block
  ↓
$: if ($theme) { applyTheme($theme) }
  ↓
CSS classes updated on <html> element
  ↓
All components re-render with new theme
  ↓
Preference saved to localStorage
```

### Knowledge Base Selection Flow
```
User opens workspace/knowledge
  ↓
Knowledge.svelte calls getKnowledgeBases()
  ↓
API: GET /api/knowledge
  ↓
Knowledge bases populate UI list
  ↓
User clicks "Add to Chat"
  ↓
selectedKnowledge store updated
  ↓
MessageInput includes knowledge IDs in requests
  ↓
Backend queries collections via queryCollection()
  ↓
Relevant chunks injected into LLM context
```

### Admin User Management Flow
```
Admin opens admin/settings/users
  ↓
Users.svelte calls getUsers()
  ↓
API: GET /api/users
  ↓
User list rendered in table
  ↓
Admin clicks "Edit" on user
  ↓
Modal opens with user form
  ↓
Admin changes role to 'admin'
  ↓
updateUserById(token, userId, { role: 'admin' })
  ↓
API: POST /api/users/{id}/update
  ↓
Backend updates user record
  ↓
Component refreshes user list
  ↓
Table shows updated role
```

## Important Notes

### Critical Dependencies
- All components require Svelte 4.x
- Stores must be initialized before component mount
- Token in localStorage required for authenticated actions
- Socket connection required for real-time features

### Performance Considerations
- Virtual scrolling for long chat histories (Messages.svelte)
- Debounced search inputs to reduce API calls
- Lazy loading for modal content
- Image lazy loading via `loading="lazy"`
- Markdown rendering can be expensive; consider memoization

### Responsive Design
- Mobile breakpoint: `$mobile` store (triggered at 768px)
- Touch-friendly tap targets (minimum 44px)
- Sidebar collapses to drawer on mobile
- Horizontal scrolling for code blocks

### Accessibility
- Semantic HTML elements (`<button>`, `<nav>`, `<main>`)
- ARIA labels on icon-only buttons
- Keyboard navigation support (Tab, Enter, Escape)
- Focus management in modals
- Screen reader announcements for status updates

### Security
- XSS prevention via Svelte's auto-escaping
- User-generated Markdown sanitized via DOMPurify
- File uploads validated by backend (extension whitelist)
- Admin components protected by route guards
- No inline event handlers (CSP-friendly)

### State Management
- Global state: Svelte stores (`$lib/stores`)
- Local state: Component `let` variables
- Derived state: Reactive statements (`$:`)
- Temporary state: sessionStorage for drafts
- No Vuex/Redux needed (Svelte stores sufficient)

### Component Lifecycle
- `onMount()` - Initial data fetching, event listeners
- `onDestroy()` - Cleanup subscriptions, event listeners
- `beforeUpdate()` - Pre-render logic
- `afterUpdate()` - Post-render DOM manipulation
- Reactive statements run automatically on dependency changes

### Testing Considerations
- Components testable via `@testing-library/svelte`
- Mock stores for isolated testing
- Mock API functions via `vi.mock()` in Vitest
- Snapshot testing for static components
- Integration tests for flows (upload → chat → response)
