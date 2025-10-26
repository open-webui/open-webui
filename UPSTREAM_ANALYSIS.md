# Open WebUI Upstream Analysis Report
## Fork Divergence Analysis (5fbfe2bdc → upstream/main)

**Analysis Date:** October 26, 2025  
**Commits Behind:** 951 commits  
**Time Period:** August 2025 → October 2025  

---

## Executive Summary

Your fork has diverged significantly from upstream over 951 commits. While the token usage tracking system you've implemented uses reasonable patterns, there are **critical breaking changes** in the upstream codebase that will affect all three custom features:

1. **WebSocket Event Names Changed**: `chat-events` → `events` 
2. **User Model Extended**: New fields `username`, `bio`, `gender`, `date_of_birth` added via migration
3. **Socket Emitter Behavior Changed**: Exclusion logic for `local:` chats added
4. **Middleware Architecture Modernized**: New MCP client support, tool result processing refactored
5. **New Migrations**: 4 new database migrations that must be applied

**Impact on Your Custom Features:**
- Token Usage Tracking: Mostly compatible, but middleware changes require updates
- Reasoning Effort Selection: Needs minor updates for new user fields
- Live Usage Display: Will break due to socket event name change

---

## Detailed Change Analysis

### 1. BREAKING: WebSocket Event Names Refactored

**Status: CRITICAL - Will Break Live Usage Display**

#### Changes in upstream/main:

**Backend Socket Handler Changes** (`backend/open_webui/socket/main.py`):
```python
# UPSTREAM: Line 359 (RENAMED)
@sio.on("events:channel")  # Was: "channel-events"
async def channel_events(sid, data):

# UPSTREAM: Line 661 (RENAMED)
emit_tasks = [
    sio.emit(
        "events",  # Was: "chat-events"
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "data": event_data,
        },
        to=session_id,
    )
]

# UPSTREAM: Line 773 (RENAMED)
response = await sio.call(
    "events",  # Was: "chat-events"
    {...}
)
```

**Frontend Listener Changes** (`src/lib/components/chat/Chat.svelte`):
```javascript
// UPSTREAM: Line 534 (CHANGED)
$socket?.on('events', chatEventHandler);  // Was: 'chat-events'

// CLEANUP: Line 621 (CHANGED)
$socket?.off('events', chatEventHandler);  // Was: 'chat-events'
```

**Your Fork Currently:**
- Backend still emits `chat-events` (line 718, 739 in socket/main.py)
- Frontend still listens to `chat-events` (line 514, 588 in Chat.svelte)
- **Token usage WebSocket emissions will break** if you don't update event names

**Required Changes for Your Fork:**
1. Update all backend `sio.emit("chat-events",` → `sio.emit("events",`
2. Update all backend `sio.call("chat-events",` → `sio.call("events",`
3. Update frontend listeners: `$socket?.on('chat-events'` → `$socket?.on('events'`
4. Update frontend listeners: `$socket?.off('chat-events'` → `$socket?.off('events'`

**Affected Files:**
- `/backend/open_webui/socket/main.py` (6 occurrences)
- `/src/lib/components/chat/Chat.svelte` (2 occurrences)

---

### 2. BREAKING: Socket Session Pool Exclusion Logic

**Status: MEDIUM - May Affect Token Usage Tracking**

**Changes in upstream/main** (`backend/open_webui/socket/main.py`):

```python
# UPSTREAM: Line 722-734
# New parameter-based exclusion
emit_tasks = [
    sio.emit(
        "events",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "data": event_data,
        },
        to=session_id,
    )
    for session_id in session_ids
]

# UPSTREAM: Line 781-784
# New condition to skip database updates for local chats
if (
    update_db
    and message_id
    and not request_info.get("chat_id", "").startswith("local:")
):
```

**Your Token Usage Implementation:**
- Your `get_event_emitter()` calls currently UPDATE DATABASE for all chats
- Upstream now **skips database updates** for `local:` prefixed chats
- This won't break your token tracking, but it's a compatibility consideration for future local-only chats

**No immediate action required**, but be aware this pattern exists.

---

### 3. NEW: User Model Extended with Profile Fields

**Status: MEDIUM - Affects Reasoning Effort & MessageInput**

**New Migration** (`backend/open_webui/migrations/versions/3af16a1c9fb6_update_user_table.py`):

```python
def upgrade() -> None:
    op.add_column("user", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("user", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("gender", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("date_of_birth", sa.Date(), nullable=True))
```

**Updated UserModel** (`backend/open_webui/models/users.py`):

```python
class UserModel(BaseModel):
    id: str
    name: str
    email: str
    username: Optional[str] = None  # NEW
    
    role: str = "pending"
    profile_image_url: str
    
    bio: Optional[str] = None  # NEW
    gender: Optional[str] = None  # NEW
    date_of_birth: Optional[datetime.date] = None  # NEW
    
    info: Optional[dict] = None
    settings: Optional[UserSettings] = None
    api_key: Optional[str] = None
    oauth_sub: Optional[str] = None
    
    last_active_at: int
    updated_at: int
    created_at: int

# NEW: UpdateProfileForm for managing these new fields
class UpdateProfileForm(BaseModel):
    profile_image_url: str
    name: str
    bio: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
```

**Impact on Your Custom Features:**

**MessageInput.svelte (Reasoning Effort):**
- Your current implementation processes template variables like `{{USER_NAME}}`
- **NEW template variables added in upstream:**
  ```javascript
  {{USER_BIO}}
  {{USER_GENDER}}
  {{USER_BIRTH_DATE}}
  {{USER_AGE}}  // calculated from date_of_birth
  ```
- Socket exclusion in `SESSION_POOL` excludes these new fields:
  ```python
  # UPSTREAM: Line 272-275
  SESSION_POOL[sid] = user.model_dump(
      exclude=["date_of_birth", "bio", "gender"]
  )
  ```
  This prevents these sensitive fields from being exposed in WebSocket sessions.

**Required Updates:**
1. Apply new migration: `3af16a1c9fb6_update_user_table.py`
2. Update your `UserModel` handling if you extend it
3. Your MessageInput template variable handler should work fine—upstream already supports new variables

---

### 4. NEW: Middleware Tool Result Processing Refactored

**Status: MEDIUM - Affects if You Use Tools in Token Counting**

**New Function in middleware.py** (`backend/open_webui/utils/middleware.py`):

```python
# UPSTREAM: Lines 125-275
def process_tool_result(
    request,
    tool_function_name,
    tool_result,
    tool_type,
    direct_tool=False,
    metadata=None,
    user=None,
):
    """
    NEW: Unified tool result processing with:
    - HTMLResponse handling
    - MCP tool result mapping
    - File/embed extraction
    """
    tool_result_embeds = []
    tool_result_files = []
    
    # Handle HTMLResponse inline/display
    if isinstance(tool_result, HTMLResponse):
        # Extract content based on Content-Disposition header
        ...
    
    # Handle tuple responses with headers (external tools)
    elif (tool_type == "external" and isinstance(tool_result, tuple)):
        tool_result, tool_response_headers = tool_result
        # Process Content-Type, Content-Disposition, Location headers
        ...
    
    # Handle MCP tool responses (list format)
    if isinstance(tool_result, list):
        if tool_type == "mcp":  # NEW: MCP support
            # Convert MCP response format
            ...
    
    # Convert dict/list to JSON string
    if isinstance(tool_result, dict) or isinstance(tool_result, list):
        tool_result = json.dumps(tool_result, indent=2, ensure_ascii=False)
    
    return tool_result, tool_result_files, tool_result_embeds
```

**Integration in chat_completion_tools_handler**:

```python
# UPSTREAM: Lines 423-447
tool_result, tool_result_files, tool_result_embeds = (
    process_tool_result(
        request,
        tool_function_name,
        tool_result,
        tool_type,
        direct_tool,
        metadata,
        user,
    )
)

# NEW: Event emission for tool results
if event_emitter:
    if tool_result_files:
        await event_emitter({
            "type": "files",
            "data": {"files": tool_result_files},
        })
    
    if tool_result_embeds:
        await event_emitter({
            "type": "embeds",
            "data": {"embeds": tool_result_embeds},
        })
```

**Impact on Token Usage Tracking:**
- Your `get_event_emitter()` now receives calls from multiple event types:
  - `"type": "chat:completion"`
  - `"type": "status"` (existing)
  - `"type": "files"` (NEW)
  - `"type": "embeds"` (NEW)
  - `"type": "source"` and `"type": "citation"` (enhanced)
- Your stream_options middleware correctly sets `include_usage: True`
- **No breaking changes**, but be aware of new event types being emitted

---

### 5. MEDIUM: MessageInput Component Significant Refactor

**Status: MEDIUM - Reasoning Effort Feature Implications**

**Major Changes in upstream**:

1. **Removed Libraries:**
   - Removed: `pdfjs-dist` imports (PDF handling moved elsewhere)
   - Removed: `heic2any` imports (HEIC conversion moved to utility)
   - Removed: `Commands.svelte` import (replaced with inline suggestions)

2. **New Features:**
   - `convertHeicToJpeg()` utility instead of heic2any
   - `getAge()` utility for calculating age from date_of_birth
   - `IntegrationsMenu.svelte` for OAuth/integration support
   - `CommandSuggestionList.svelte` for command autocomplete
   - `ValvesModal.svelte` for tool configuration

3. **Reactive Changes:**
   - Input variables modal now returns via Promise instead of event handler
   - `setText()` method now accepts optional callback: `setText(text, callback)`
   - Removed rich text conditional logic (now always uses RichTextInput)

4. **Template Variable Processing:**
   ```javascript
   // UPSTREAM: NEW variables added
   if (text.includes('{{USER_BIO}}')) {
       const bio = sessionUser?.bio || '';
       if (bio) text = text.replaceAll('{{USER_BIO}}', bio);
   }
   
   if (text.includes('{{USER_GENDER}}')) {
       const gender = sessionUser?.gender || '';
       if (gender) text = text.replaceAll('{{USER_GENDER}}', gender);
   }
   
   if (text.includes('{{USER_AGE}}')) {
       const birthDate = sessionUser?.date_of_birth || '';
       if (birthDate) {
           const age = getAge(birthDate);
           text = text.replaceAll('{{USER_AGE}}', age);
       }
   }
   ```

**Your Reasoning Effort Implementation:**
- Currently stored in `reasoningEffortByModel` localStorage object
- Passed to backend in payload: `reasoning: { effort: reasoningEffort }`
- Upstream **does NOT implement** reasoning effort UI—this is YOUR custom feature!

**Required Updates:**
1. Your reasoning effort feature is **NOT in upstream**, so you'll need to manually integrate it with the refactored MessageInput
2. The new `getAge()` utility might be useful if you use `{{USER_AGE}}`
3. New `IntegrationsMenu.svelte` and `ValvesModal.svelte` are orthogonal—won't conflict

---

### 6. MODERATE: Chat Component Major Refactoring

**Status: MODERATE - Affects Event Handling & Usage Display**

**Key Changes in upstream** (`src/lib/components/chat/Chat.svelte`):

1. **Store Changes:**
   - Added: `functions` store
   - Added: `pinnedChats` store
   - Added: `showEmbeds` store
   - Removed imports: `mermaid` (no longer used)

2. **Event Handler Changes:**
   ```javascript
   // UPSTREAM: Lines 356-361
   } else if (type === 'chat:tasks:cancel') {
       taskIds = null;
       const responseMessage = history.messages[history.currentId];
       // Set all response messages to done
       for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
           history.messages[messageId].done = true;
       }
   } else if (type === 'chat:message:delta' || type === 'message') {
       message.content += data.content;
   } else if (type === 'chat:message' || type === 'replace') {
       message.content = data.content;
   } else if (type === 'chat:message:files' || type === 'files') {
       message.files = data.files;
   } else if (type === 'chat:message:embeds' || type === 'embeds') {  # NEW
       message.embeds = data.embeds;
   } else if (type === 'chat:message:error') {  # NEW
       message.error = data.error;
   ```

3. **Socket Event Listener:**
   ```javascript
   // UPSTREAM: Line 534 (CRITICAL FOR YOU)
   $socket?.on('events', chatEventHandler);  // CHANGED from 'chat-events'
   ```

4. **New Lifecycle Features:**
   - Model selection saved to folder: `updateFolderById()` call
   - Task cancellation handling for parallel completions
   - Default tools/filters/features loaded per model

**Impact on Your Live Usage Display:**
- Your usage display likely listens to socket `'usage'` event (not `'chat-events'`)
- **Verify your usage WebSocket integration doesn't rely on 'chat-events'**
- New event types (`chat:tasks:cancel`, `chat:message:embeds`) are additions, not breaking

---

### 7. NEW: Four Database Migrations

**Status: IMPORTANT - Must Be Applied**

**New Migrations in upstream:**

1. **018012973d35_add_indexes.py**
   - Adds database indexes for performance optimization
   - No schema changes

2. **38d63c18f30f_add_oauth_session_table.py**
   - Adds `OAuthSession` table for OAuth token management
   - Non-breaking

3. **3af16a1c9fb6_update_user_table.py** (DISCUSSED ABOVE)
   - Adds: `username`, `bio`, `gender`, `date_of_birth` columns
   - **You must apply this for new user fields to work**

4. **a5c220713937_add_reply_to_id_column_to_message.py**
   - Adds `reply_to_id` column to message table
   - Enables message threading feature

**Your Fork's Current Migration Status:**
- Last migration: `e223b100ad81_add_reset_scheduling_to_token_groups.py` (Oct 26)
- Missing 4 upstream migrations
- Your custom token_usage migration is **after** the new user migration in revision order
- **Action: Apply all 4 new migrations before running your fork**

---

### 8. MODERATE: Stream Options & Delta Chunk Size Support

**Status: MODERATE - Your Token Usage Feature Already Handles This**

**Middleware Changes** (`backend/open_webui/utils/middleware.py`):

Your current implementation:
```python
# Your code in middleware.py (line ~735-744)
# Ensure stream_options.include_usage is enabled for token usage tracking
if stream_response:
    if "stream_options" not in form_data:
        form_data["stream_options"] = {}
    form_data["stream_options"]["include_usage"] = True
```

Upstream also implements:
```python
# UPSTREAM: Lines 950-953
def apply_params_to_form_data(form_data, model):
    open_webui_params = {
        "stream_response": bool,
        "stream_delta_chunk_size": int,  # NEW
        "function_calling": str,
        "reasoning_tags": list,  # NEW
        "system": str,
    }
```

**New parameter support:**
- `stream_delta_chunk_size` - Controls chunk granularity in streaming responses
- `reasoning_tags` - Defines tags for thinking blocks (e.g., `<think>`, `<reasoning>`)

**Impact on Your Token Usage:**
- Your implementation is compatible
- No breaking changes; new parameters are additions
- Your `include_usage: True` setting will continue to work

---

### 9. NEW: MCP (Model Context Protocol) Client Support

**Status: LOW PRIORITY - Doesn't Affect Token Tracking**

**New in Middleware** (`backend/open_webui/utils/middleware.py`):

Upstream adds MCP server integration:
```python
from open_webui.utils.mcp.client import MCPClient

# UPSTREAM: Lines 1200-1290
if tool_id.startswith("server:mcp:"):
    server_id = tool_id[len("server:mcp:"):]
    
    # Load MCP server connection config
    mcp_server_connection = None
    for server_connection in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        if (
            server_connection.get("type", "") == "mcp"
            and server_connection.get("info", {}).get("id") == server_id
        ):
            mcp_server_connection = server_connection
            break
    
    # Connect to MCP server
    mcp_clients[server_id] = MCPClient()
    await mcp_clients[server_id].connect(
        url=mcp_server_connection.get("url", ""),
        headers=headers if headers else None,
    )
    
    tool_specs = await mcp_clients[server_id].list_tool_specs()
```

**Your Token Usage:** Not affected. MCP is a new tool execution backend.

---

### 10. MODERATE: Middleware Pipeline Enhancements

**Status: MODERATE - Review for Compatibility**

**New Features in upstream middleware:**

1. **System Prompt Application via `apply_system_prompt_to_body()`:**
   ```python
   # UPSTREAM: Lines 1001-1012
   system_message = get_system_message(form_data.get("messages", []))
   if system_message:
       form_data = apply_system_prompt_to_body(
           system_message.get("content"), 
           form_data, 
           metadata, 
           user, 
           replace=True
       )
   ```

2. **OAuth Token Integration:**
   ```python
   # UPSTREAM: Lines 1014-1024
   oauth_token = None
   try:
       if request.cookies.get("oauth_session_id", None):
           oauth_token = await request.app.state.oauth_manager.get_oauth_token(
               user.id,
               request.cookies.get("oauth_session_id", None),
           )
   except Exception as e:
       log.error(f"Error getting OAuth token: {e}")
   
   extra_params["__oauth_token__"] = oauth_token
   ```

3. **File Context Mode Support:**
   ```python
   # UPSTREAM: Lines 810-830
   # Check if all files are in full context mode
   all_full_context = all(item.get("context") == "full" for item in files)
   
   if not all_full_context:
       # ... normal query generation ...
   ```

**Your Token Usage:**
- Not directly affected
- Ensure your `get_event_emitter()` calls pass through correctly
- `__event_emitter__` and `__event_call__` are still in `extra_params`

---

## Summary of Breaking Changes

| Feature | Status | Impact | Action Required |
|---------|--------|--------|-----------------|
| WebSocket Event Names | CRITICAL | `chat-events` → `events` | Update socket listeners in backend & frontend |
| User Model Fields | MEDIUM | 4 new profile fields added | Apply migration, update template variable handler |
| Chat Component Event Types | MEDIUM | New event types for embeds/error | Add handlers for new event types |
| MessageInput Refactor | MEDIUM | Component restructured | Manually integrate reasoning effort UI |
| Database Migrations | IMPORTANT | 4 new migrations to apply | Run Alembic migrations |
| Stream Options | MEDIUM | New `stream_delta_chunk_size` param | Already compatible via your middleware |
| Socket Exclusion Logic | LOW | `local:` chat handling | No action needed |
| MCP Support | LOW | New tool server type | No action needed for token tracking |
| Files Context Mode | LOW | New RAG file mode | No action needed |

---

## Custom Feature Status

### 1. Token Usage Tracking System
**Status: MOSTLY COMPATIBLE ✓**

**What Works:**
- Your database schema (TokenGroup, TokenUsage) is independent
- Your migration strategy works (after user table migration)
- Your middleware integration with `stream_options.include_usage` is solid
- WebSocket emission via `get_event_emitter()` remains compatible

**What Needs Updating:**
1. Update WebSocket event name from `chat-events` to `events` if you emit token usage via socket
2. Ensure your token_groups router is registered in main.py (if present)
3. Verify migration order: your token migration must come after `3af16a1c9fb6_update_user_table.py`

**Migration Order (Critical):**
```
018012973d35_add_indexes.py
38d63c18f30f_add_oauth_session_table.py
3af16a1c9fb6_update_user_table.py  ← User fields
a5c220713937_add_reply_to_id_column_to_message.py
YOUR: e223b100ad81_add_reset_scheduling_to_token_groups.py
```

### 2. Reasoning Effort Selection UI
**Status: COMPATIBLE, NEEDS INTEGRATION ✓**

**What Works:**
- Your localStorage-based reasoning effort tracking
- Your payload injection: `reasoning: { effort: reasoningEffort }`
- Backend doesn't break existing parameters

**What Needs Updating:**
1. Integrate reasoning effort UI with refactored MessageInput component
2. Remove old imports (pdfjs, heic2any if using them)
3. Adapt to new `setText()` method signature: `setText(text, callback)`
4. Add new template variable support if desired: `{{USER_BIO}}`, `{{USER_AGE}}`

**Code Changes Required:**
```javascript
// Your current onChange approach
export let onChange: Function = () => {};

// Update to match upstream's callback pattern
const inputVariableHandler = async (text: string): Promise<string> => {
    // ... handle variables ...
    return text;  // Must return Promise
};

// Update setText() calls
messageInput?.setText(text, async () => {
    if (!($settings?.insertSuggestionPrompt ?? false)) {
        await tick();
        submitPrompt(prompt);
    }
});
```

### 3. Live Usage Display
**Status: WILL BREAK - CRITICAL ❌**

**What Breaks:**
- Any code listening to `$socket.on('chat-events', ...)` will stop receiving events
- Must update to `$socket.on('events', ...)`

**Required Updates:**
- Search your codebase for: `socket.on('chat-events'` → change to `socket.on('events'`
- Search for: `socket.off('chat-events'` → change to `socket.off('events'`
- Search for: `$socket?.on('chat-events'` → change to `$socket?.on('events'`

---

## Implementation Roadmap

### Phase 1: Database Migrations (BEFORE upgrading)
1. Back up your database
2. Apply upstream migrations in order:
   ```bash
   # From backend directory
   alembic upgrade 3af16a1c9fb6  # User profile fields
   alembic upgrade a5c220713937  # Message reply_to
   # ... other migrations ...
   ```
3. Ensure your token_usage migration comes after

### Phase 2: Backend Updates
1. Update `socket/main.py`:
   - Change `"chat-events"` → `"events"` (6 occurrences)
   - Change `"channel-events"` → `"events:channel"` (1 occurrence)

2. Verify token usage router is registered in `main.py`:
   ```python
   from open_webui.routers import usage  # if you have one
   app.include_router(usage.router, prefix="/api")
   ```

3. Update middleware.py stream_options (should be compatible already)

### Phase 3: Frontend Updates
1. Update `Chat.svelte`:
   - Change line 514: `$socket?.on('chat-events'` → `$socket?.on('events'`
   - Change line 588: `$socket?.off('chat-events'` → `$socket?.off('events'`

2. Find any other socket listeners in your codebase:
   ```bash
   # Search for old event name
   grep -r "chat-events" src/
   grep -r "'chat-events'" src/
   ```

3. Update MessageInput.svelte for reasoning effort feature:
   - Remove pdfjs/heic2any imports if present
   - Update `setText()` call signature with callback
   - Keep reasoning effort logic as-is (it's your custom feature)

### Phase 4: Testing
1. Test WebSocket connection and real-time updates
2. Test token usage tracking with new event system
3. Test reasoning effort selection (verify payload received)
4. Test user template variables if implemented

---

## Files That Need Updates in Your Fork

### Backend Files:
- `/backend/open_webui/socket/main.py` - Update event names (6 places)
- `/backend/open_webui/main.py` - Register any new routers (if needed)
- `/backend/open_webui/utils/middleware.py` - Already compatible, verify stream_options

### Frontend Files:
- `/src/lib/components/chat/Chat.svelte` - Update socket listener (2 places)
- `/src/lib/components/chat/MessageInput.svelte` - Integrate with refactored component
- Any custom usage display components - Update socket listeners

### Database:
- Run 4 new migrations from upstream (apply them in order)
- Your token_usage migration must come after user table migration

---

## Recommendations

### For Immediate Sync (Minimal Risk):
1. Apply the 4 upstream migrations
2. Update WebSocket event names (`chat-events` → `events`)
3. Test token usage and usage display
4. Keep reasoning effort as-is (custom feature, no upstream version)

### For Full Sync (More Risk):
1. Do everything above
2. Merge latest MessageInput component updates
3. Merge latest Chat component updates
4. Run comprehensive testing

### For Long-Term Maintenance:
1. Consider upstreaming your custom features if valuable to community
2. Implement automated test suite for socket event handling
3. Monitor upstream commits weekly for major breaking changes
4. Maintain a CHANGELOG for custom fork features

---

## Testing Checklist

Before merging upstream changes:

- [ ] WebSocket connection established with `events` event listener
- [ ] Real-time chat message streaming works
- [ ] Token usage displayed correctly in UI
- [ ] Reasoning effort selection saves and loads from localStorage
- [ ] New user profile fields (bio, gender, date_of_birth) don't break existing flows
- [ ] File uploads with RAG still work
- [ ] Tool execution and results display correctly
- [ ] All 4 new migrations applied successfully
- [ ] No TypeScript compilation errors
- [ ] No console errors in browser dev tools

---

## Conflict Resolution Strategy

If you encounter merge conflicts:

1. **socket/main.py conflicts**: Keep your token tracking logic, accept upstream event name changes
2. **MessageInput.svelte conflicts**: Keep your reasoning effort logic, merge upstream template variable handling
3. **Chat.svelte conflicts**: Keep your usage display logic, accept upstream event handler changes
4. **middleware.py conflicts**: Your stream_options code is compatible; accept upstream enhancements

