# Backend Socket Directory

This directory implements real-time WebSocket communication using Socket.IO, enabling bidirectional event-based messaging between frontend clients and backend services. It manages user sessions, collaborative document editing (via Yjs/CRDT), chat event streaming, and token usage tracking across distributed deployments using Redis.

## Files

### main.py
Primary Socket.IO server implementation with event handlers and session management.

**Key Functions:**
- `sio` - AsyncServer instance for Socket.IO
- `app` - ASGI application mounted at `/ws` route
- `get_event_emitter()` - Returns async function for broadcasting chat events
- `get_event_call()` - Request-response style event communication
- `get_active_user_ids()` - List of currently connected users
- `get_models_in_use()` - Track active model usage

**Socket.IO Event Handlers:**
- `connect(sid, environ, auth)` - Authenticate via JWT, populate SESSION_POOL
- `user-join` - Alternative join handler with channel subscriptions
- `channel-events` - Broadcast channel activity (typing, etc.)
- `ydoc:document:join/update/leave` - Collaborative editing via Yjs
- `ydoc:awareness:update` - Cursor/selection sync for editors
- `usage` - Token usage tracking from clients
- `disconnect(sid)` - Session cleanup

**Used by:**
- `routers/chats.py` - Emits chat-events for real-time message updates
- `routers/channels.py` - Broadcasts channel messages
- `utils/middleware.py` - Streams LLM completions and tool execution
- Frontend: `src/lib/stores/index.ts` - Socket client connection

**Uses:**
- `models/users.py` - User authentication via JWT
- `models/channels.py` - Channel subscriptions
- `models/chats.py` - Chat message persistence
- `models/notes.py` - Note document updates
- `utils/redis.py` - Redis connection for distributed mode
- `utils/auth.py` - decode_token()

**Returns to Frontend:**
Socket events with structure:
```javascript
{
  type: "chat:completion" | "chat:message:delta" | "status",
  data: { content, done, sources, usage, ... }
}
```

### utils.py
Utility classes for Redis-backed session management and collaborative editing.

**Classes:**
- `RedisLock` - Distributed lock for coordinating cleanup tasks
- `RedisDict` - Dict interface backed by Redis hash
- `YdocManager` - Manages Yjs document state and active collaborators

**Used by:**
- `socket/main.py` - Session pools, document management

**Uses:**
- `utils/redis.py` - get_redis_connection()
- `pycrdt` - CRDT operations for Yjs

## Architecture & Patterns

### Session Management
**Two-Tier Pooling:**
```python
SESSION_POOL[sid] = user_object  # Socket ID → User
USER_POOL[user_id] = [sid1, sid2, ...]  # User → Sessions
```

Enables broadcasting to all user's connected clients (multi-tab support).

### Event Emission Pattern
```python
emit_fn = get_event_emitter(request_info)
await emit_fn({
    "type": "chat:completion",
    "data": {"content": "Hello", "done": False}
})
```

Emitter closure captures context, broadcasts to user's sessions, optionally persists to database.

### Collaborative Editing (Yjs/CRDT)
**Flow:**
1. Frontend joins document: `socket.emit("ydoc:document:join", {document_id, user_id})`
2. Server loads history from `YDOC_MANAGER`
3. Server sends state: `socket.on("ydoc:document:state")`
4. Edits: `socket.emit("ydoc:document:update", {document_id, update})`
5. Server broadcasts to room `doc_{document_id}` except sender
6. Debounced save (0.5s) calls `Notes.update_note_by_id()`

### Token Usage Tracking
**Pattern:**
```
Frontend: socket.emit('usage', {model, usage: {prompt_tokens, completion_tokens}})
  ↓
Backend: Aggregates by token groups
  ↓
Updates: token_groups.update_token_usage(model, IN, OUT, TOTAL)
  ↓
Periodic cleanup: Removes stale entries (3+ seconds old)
```

### Dual Backend Support
**In-Memory Mode:**
- Single instance deployments
- Dict-based SESSION_POOL, USER_POOL

**Redis Mode:**
- Multi-instance deployments
- RedisDict for shared state
- Distributed locks prevent race conditions

## Integration Points

### Frontend WebSocket Connection
```javascript
// In src/lib/stores/index.ts
import io from 'socket.io-client';

socket = io('/ws/socket.io', {
    auth: { token: localStorage.token }
});

socket.on('chat-events', (data) => {
    // Handle streaming completion
});
```

### Chat Completion Flow
```
User sends message
  ↓
POST /api/chat/completions
  ↓
Router creates emit_fn = get_event_emitter(metadata)
  ↓
LLM streams response
  ↓
emit_fn({ type: "chat:message:delta", data: { content } })
  ↓
Socket broadcasts to user's sessions
  ↓
Frontend updates UI in real-time
```

### Collaborative Note Editing
```
User opens note → Join document room
  ↓
socket.emit("ydoc:document:join")
  ↓
Server loads Yjs state from Redis/memory
  ↓
Server responds with document state
  ↓
User edits → socket.emit("ydoc:document:update")
  ↓
Server broadcasts to collaborators
  ↓
Debounced save to Notes.update_note_by_id()
```

### Channel Events
```
User types in channel
  ↓
socket.emit("channel-events", {channel_id, type: "typing"})
  ↓
Server broadcasts to channel room
  ↓
Other users see typing indicator
```

## Key Workflows

### Connection Lifecycle
```
1. Client connects with JWT token
2. connect() handler validates token
3. Populate SESSION_POOL[sid] and USER_POOL[user_id]
4. Optional: user-join emits subscribed channels
5. Client receives acknowledgment
6. Bidirectional events flow
7. On disconnect: Cleanup pools and document collaborators
```

### Event Broadcast Strategies
**Single User:**
```python
sids = USER_POOL.get(user_id, [])
for sid in sids:
    await sio.emit("event", data, to=sid)
```

**Room-based (Channel/Document):**
```python
await sio.emit("event", data, room=f"channel:{id}", skip_sid=sender_sid)
```

### Token Usage Periodic Cleanup
```
Every 3 seconds:
  1. Acquire distributed lock (if Redis mode)
  2. Scan USAGE_POOL for stale entries
  3. Remove entries older than 3 seconds
  4. Release lock
```

## Important Notes

**Critical Dependencies:**
- Socket must authenticate via JWT; invalid token rejects connection
- Redis required for multi-instance deployments (WEBSOCKET_MANAGER=redis)
- Yjs document updates stored in Redis lists or in-memory

**Performance Considerations:**
- Session pools grow with connected users; cleanup on disconnect critical
- Document history unbounded; very long-lived docs can consume memory
- Token usage polling every 3 seconds per instance

**Security:**
- JWT validation prevents unauthorized connections
- Channel join verifies user has access via `Channels.get_channels_by_user_id()`
- Note join validates access via `has_access()` check

**Gotchas:**
- No session recovery on server restart (clients must reconnect)
- Yjs updates broadcast immediately (no queuing); slow servers = out-of-order updates
- Awareness (cursor) updates ephemeral (not persisted)
- Token usage only tracks socket-emitted events (offline requests not counted)
