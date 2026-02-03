# ADR 005: Socket.IO for Real-Time Communication

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI requires real-time features:
- **Message streaming:** Token-by-token display during LLM response generation
- **Usage tracking:** Live model utilization across connected users
- **Channel messaging:** Real-time group chat and direct messages
- **Collaborative editing:** Concurrent note editing (YCRDT)
- **Presence indicators:** Online/away user status

These features require bidirectional communication between server and client, with support for:
- Automatic reconnection on network issues
- Room-based message routing (per-user, per-channel)
- Scalability across multiple server instances

## Decision

Use **Socket.IO** (python-socketio) for WebSocket-based real-time communication.

Key characteristics leveraged:
- Automatic fallback to HTTP long-polling when WebSockets unavailable
- Room abstraction for targeted message delivery
- Redis adapter for multi-instance deployments
- Mature ecosystem with good client library support

## Consequences

### Positive
- **Reliability:** Automatic reconnection and fallback mechanisms
- **Scalability:** Redis adapter enables horizontal scaling
- **Simplicity:** Room-based routing matches our user/channel model
- **Client support:** Official Svelte-compatible client library

### Negative
- **Overhead:** Socket.IO protocol adds framing overhead vs raw WebSockets
- **Complexity:** Additional infrastructure (Redis) for multi-instance
- **Debugging:** Real-time issues harder to reproduce and trace
- **State management:** Must sync WebSocket state with HTTP session

### Neutral
- Requires understanding of event-driven patterns
- Additional monitoring needed for connection health

## Implementation

**Server setup:**

```python
# socket/main.py
import socketio

sio = socketio.AsyncServer(
    cors_allowed_origins=CORS_ALLOW_ORIGINS,
    async_mode="asgi",
    transports=["websocket", "polling"],
    client_manager=socketio.AsyncRedisManager(REDIS_URL) if REDIS_URL else None,
)

# Create ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")

# Mount on FastAPI
app.mount("/ws", socket_app)
```

**Event handlers:**

```python
# Connection management
@sio.event
async def connect(sid, environ, auth):
    if auth and "token" in auth:
        user = validate_token(auth["token"])
        if user:
            SESSION_POOL[sid] = user
            await sio.enter_room(sid, f"user:{user.id}")

@sio.event
async def disconnect(sid):
    SESSION_POOL.pop(sid, None)

# Custom events
@sio.on("usage")
async def usage(sid, data):
    """Track model usage in real-time"""
    model_id = data["model"]
    USAGE_POOL[model_id][sid] = {"updated_at": time.time()}

@sio.on("user-join")
async def user_join(sid, data):
    """User joins a specific context"""
    user = SESSION_POOL.get(sid)
    await sio.enter_room(sid, f"chat:{data['chat_id']}")
```

**Emitting to users:**

```python
async def notify_user(user_id: str, event: str, data: dict):
    """Send event to specific user across all their connections"""
    await sio.emit(event, data, room=f"user:{user_id}")

async def broadcast_to_channel(channel_id: str, event: str, data: dict):
    """Send event to all channel members"""
    await sio.emit(event, data, room=f"channel:{channel_id}")
```

**Client integration:**

```typescript
// Frontend Socket.IO client
import { io } from 'socket.io-client';

const socket = io(WEBUI_BASE_URL, {
  path: '/ws/socket.io',
  auth: { token: userToken },
  transports: ['websocket', 'polling'],
});

socket.on('connect', () => {
  console.log('Connected');
});

socket.on('message', (data) => {
  // Handle incoming message
});
```

## Distributed Architecture

For multi-instance deployments:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Instance 1 │     │  Instance 2 │     │  Instance 3 │
│  Socket.IO  │     │  Socket.IO  │     │  Socket.IO  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │    Redis    │
                    │   Pub/Sub   │
                    └─────────────┘
```

Configuration:
```python
WEBSOCKET_MANAGER = os.environ.get("WEBSOCKET_MANAGER", "")  # "redis" for distributed
WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", REDIS_URL)
```

## Alternatives Considered

### Raw WebSockets
- Lower overhead, more control
- Manual reconnection and fallback logic
- Manual room/broadcast implementation
- Rejected due to implementation complexity

### Server-Sent Events (SSE)
- Simpler, unidirectional streaming
- Good for LLM response streaming only
- Cannot handle bidirectional channel messaging
- Used for LLM streaming, but Socket.IO needed for full real-time

### Centrifugo
- Dedicated real-time messaging server
- Additional infrastructure component
- Overkill for current scale requirements
- Rejected for operational simplicity

### Phoenix Channels (Elixir)
- Excellent real-time capabilities
- Requires Elixir runtime
- Doesn't fit Python backend architecture
- Rejected for technology stack consistency

## Related Documents

- `DIRECTIVE_adding_websocket_event.md` — How to add WebSocket events
- `ADR_012_redis_cluster_otel.md` — Distributed infrastructure
- `ARCHITECTURE_OVERVIEW.md` — System design

---

*Last updated: 2026-02-03*
