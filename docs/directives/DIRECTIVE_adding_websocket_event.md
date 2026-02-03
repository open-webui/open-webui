# Directive: Adding WebSocket Events

> **Pattern type:** Real-time feature
> **Complexity:** Medium
> **Files touched:** 2-3

---

## Prerequisites

- `ADR_005_socketio_realtime.md` — WebSocket architecture
- `SYSTEM_TOPOLOGY.md` — Real-time data flow

---

## Structural Pattern

When adding real-time features using WebSocket:

1. **Define server-side event handler** using Socket.IO decorators
2. **Emit events to specific rooms** (user, channel, etc.)
3. **Connect client-side listener** in Svelte components
4. **Handle connection state** for reliability

| Component | Location | Purpose |
|-----------|----------|---------|
| Server events | `backend/open_webui/socket/main.py` | Event handlers |
| Client connection | `src/lib/stores/index.ts` | Socket store |
| Component listener | `src/lib/components/*.svelte` | Event handling |

---

## Illustrative Application

The socket server (`backend/open_webui/socket/main.py`) demonstrates this pattern:

### Step 1: Add Server-Side Event Handler

```python
# backend/open_webui/socket/main.py
import socketio
import time
from open_webui.utils.auth import decode_token
from open_webui.models.users import Users

sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode="asgi",
)

# Session tracking
SESSION_POOL = {}  # sid -> user data


@sio.event
async def connect(sid, environ, auth):
    """Handle new connection."""
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])
        if data and "id" in data:
            user = Users.get_user_by_id(data["id"])

    if user:
        SESSION_POOL[sid] = user.model_dump()
        # Join user's personal room
        await sio.enter_room(sid, f"user:{user.id}")
        return True

    return False  # Reject connection


@sio.event
async def disconnect(sid):
    """Handle disconnection."""
    SESSION_POOL.pop(sid, None)


# Custom event: Feature update notification
@sio.on("feature:subscribe")
async def feature_subscribe(sid, data):
    """
    Client subscribes to feature updates.

    Args:
        data: {"feature_id": "xxx"}
    """
    if sid not in SESSION_POOL:
        return {"error": "Not authenticated"}

    feature_id = data.get("feature_id")
    if feature_id:
        await sio.enter_room(sid, f"feature:{feature_id}")
        return {"status": "subscribed", "feature_id": feature_id}


@sio.on("feature:unsubscribe")
async def feature_unsubscribe(sid, data):
    """Client unsubscribes from feature updates."""
    feature_id = data.get("feature_id")
    if feature_id:
        await sio.leave_room(sid, f"feature:{feature_id}")
        return {"status": "unsubscribed"}


# Server-side emit function (call from routers)
async def notify_feature_update(feature_id: str, data: dict):
    """
    Notify all subscribers of a feature update.

    Call this from API endpoints after feature changes.
    """
    await sio.emit(
        "feature:updated",
        {"feature_id": feature_id, "data": data},
        room=f"feature:{feature_id}"
    )


async def notify_user(user_id: str, event: str, data: dict):
    """Send event to specific user across all their connections."""
    await sio.emit(event, data, room=f"user:{user_id}")
```

### Step 2: Call from API Endpoints

```python
# backend/open_webui/routers/features.py
from open_webui.socket.main import notify_feature_update, notify_user

@router.put("/{feature_id}")
async def update_feature(
    feature_id: str,
    body: FeatureUpdate,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Update feature and notify subscribers."""
    # Update in database
    feature = Features.update_feature(feature_id, body, db=db)

    # Notify via WebSocket
    await notify_feature_update(feature_id, feature.model_dump())

    return feature
```

### Step 3: Connect Client-Side

```typescript
// src/lib/stores/index.ts
import { writable } from 'svelte/store';
import { io, type Socket } from 'socket.io-client';
import { WEBUI_BASE_URL } from '$lib/constants';

export const socket = writable<Socket | null>(null);

export function initSocket(token: string) {
  const socketInstance = io(WEBUI_BASE_URL, {
    path: '/ws/socket.io',
    auth: { token },
    transports: ['websocket', 'polling'],
  });

  socketInstance.on('connect', () => {
    console.log('Socket connected');
  });

  socketInstance.on('disconnect', () => {
    console.log('Socket disconnected');
  });

  socket.set(socketInstance);
  return socketInstance;
}
```

### Step 4: Listen in Components

```svelte
<!-- src/lib/components/FeaturePanel.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { socket } from '$lib/stores';

  export let featureId: string;

  let featureData = null;

  onMount(() => {
    if ($socket) {
      // Subscribe to updates
      $socket.emit('feature:subscribe', { feature_id: featureId });

      // Listen for updates
      $socket.on('feature:updated', (data) => {
        if (data.feature_id === featureId) {
          featureData = data.data;
        }
      });
    }
  });

  onDestroy(() => {
    if ($socket) {
      // Unsubscribe
      $socket.emit('feature:unsubscribe', { feature_id: featureId });

      // Remove listener
      $socket.off('feature:updated');
    }
  });
</script>

{#if featureData}
  <div>{featureData.name}</div>
{/if}
```

---

## Transfer Prompt

**When you need to add real-time functionality:**

1. **Add server event handler** in `backend/open_webui/socket/main.py`:
   ```python
   @sio.on("my-event")
   async def handle_my_event(sid, data):
       if sid not in SESSION_POOL:
           return {"error": "Not authenticated"}

       # Process event
       result = process_data(data)

       # Optionally emit to rooms
       await sio.emit("my-event-result", result, room=f"user:{user_id}")

       return {"status": "success"}
   ```

2. **Create emit helper** for API use:
   ```python
   async def emit_my_event(target_id: str, data: dict):
       await sio.emit("my-event", data, room=f"target:{target_id}")
   ```

3. **Call from routers:**
   ```python
   from open_webui.socket.main import emit_my_event

   @router.post("/action")
   async def do_action(...):
       # Perform action
       await emit_my_event(target_id, {"result": "..."})
   ```

4. **Connect client listener:**
   ```svelte
   <script>
     import { socket } from '$lib/stores';

     onMount(() => {
       $socket?.on('my-event', (data) => {
         // Handle event
       });
     });

     onDestroy(() => {
       $socket?.off('my-event');
     });
   </script>
   ```

**Room patterns:**
- `user:{user_id}` — Events for specific user
- `channel:{channel_id}` — Channel messages
- `chat:{chat_id}` — Chat-specific events
- `feature:{feature_id}` — Feature subscriptions

**Signals that this pattern applies:**
- Need instant updates without polling
- Collaborative features (editing, presence)
- Live notifications
- Streaming data display

---

## Related Documents

- `ADR_005_socketio_realtime.md` — Architecture decisions
- `ADR_012_redis_cluster_otel.md` — Distributed setup
- `backend/open_webui/socket/main.py` — Reference

---

*Last updated: 2026-02-03*
