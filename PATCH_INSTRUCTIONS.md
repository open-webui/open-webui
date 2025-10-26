# Detailed Patch Instructions for Upstream Sync

## Exact Code Changes Required

### Change 1: backend/open_webui/socket/main.py

**Location 1: Line ~360 (channel events handler)**
```python
# BEFORE
@sio.on("channel-events")
async def channel_events(sid, data):

# AFTER
@sio.on("events:channel")
async def channel_events(sid, data):
```

**Location 2: Line ~376 (emit channel events)**
```python
# BEFORE
await sio.emit(
    "channel-events",
    {...},
    room=...,
    skip_sid=...
)

# AFTER
await sio.emit(
    "events:channel",
    {...},
    room=...,
    skip_sid=...
)
```

**Location 3: Line ~718 (get_event_emitter - main emit)**
```python
# BEFORE
emit_tasks = [
    sio.emit(
        "chat-events",
        {
            "chat_id": request_info.get("chat_id", None),
            "message_id": request_info.get("message_id", None),
            "data": event_data,
        },
        to=session_id,
    )
    for session_id in session_ids
]

# AFTER
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
```

**Location 4: Line ~773 (get_event_call - call)**
```python
# BEFORE
response = await sio.call(
    "chat-events",
    {
        "chat_id": request_info.get("chat_id", None),
        "message_id": request_info.get("message_id", None),
        "data": event_data,
    },
    to=session_id,
)

# AFTER
response = await sio.call(
    "events",
    {
        "chat_id": request_info.get("chat_id", None),
        "message_id": request_info.get("message_id", None),
        "data": event_data,
    },
    to=session_id,
)
```

---

### Change 2: src/lib/components/chat/Chat.svelte

**Location 1: Line ~514 (mount - socket listener)**
```svelte
<!-- BEFORE -->
$socket?.on('chat-events', chatEventHandler);

<!-- AFTER -->
$socket?.on('events', chatEventHandler);
```

**Location 2: Line ~588 (destroy - socket cleanup)**
```svelte
<!-- BEFORE -->
$socket?.off('chat-events', chatEventHandler);

<!-- AFTER -->
$socket?.off('events', chatEventHandler);
```

---

### Change 3: Apply Database Migrations

Run these in order (your fork has already run earlier migrations):

```bash
cd backend

# Check current revision
alembic current

# Apply upstream migrations
alembic upgrade 018012973d35
# Output should show: Running upgrade ... -> 018012973d35, add indexes

alembic upgrade 38d63c18f30f
# Output should show: Running upgrade 018012973d35 -> 38d63c18f30f, add oauth_session_table

alembic upgrade 3af16a1c9fb6
# Output should show: Running upgrade 38d63c18f30f -> 3af16a1c9fb6, update user table
# This adds: username, bio, gender, date_of_birth columns

alembic upgrade a5c220713937
# Output should show: Running upgrade 3af16a1c9fb6 -> a5c220713937, add reply_to_id

# Verify final state
alembic current
# Should show: a5c220713937 (head)
```

---

## Option A: Manual Editing (Safest)

1. Open `/backend/open_webui/socket/main.py` in your editor
2. Use Find & Replace (Ctrl+H / Cmd+H):
   - Find: `"chat-events"`
   - Replace: `"events"`
   - Replace ALL (should find 2 occurrences in get_event_emitter, 1 in get_event_call)

3. Use Find & Replace again:
   - Find: `"channel-events"`
   - Replace: `"events:channel"`
   - Replace ALL (should find 2 occurrences)

4. Open `/src/lib/components/chat/Chat.svelte`
5. Use Find & Replace:
   - Find: `'chat-events'`
   - Replace: `'events'`
   - Replace ALL (should find 2 occurrences)

6. Run migrations:
   ```bash
   cd backend && alembic upgrade a5c220713937
   ```

---

## Option B: Using git patches

Create a patch file for socket events:

```bash
# Generate diff
git diff > /tmp/socket-events.patch
```

Then apply it:
```bash
# Verify patch
patch -p1 --dry-run < socket-events.patch

# Apply patch
patch -p1 < socket-events.patch
```

---

## Option C: Direct sed commands (Linux/Mac)

**Warning: Use with caution, backup first**

```bash
# Backup originals
cp backend/open_webui/socket/main.py backend/open_webui/socket/main.py.bak
cp src/lib/components/chat/Chat.svelte src/lib/components/chat/Chat.svelte.bak

# Replace chat-events with events
sed -i.bak 's/"chat-events"/"events"/g' backend/open_webui/socket/main.py
sed -i.bak "s/'chat-events'/'events'/g" src/lib/components/chat/Chat.svelte

# Replace channel-events with events:channel
sed -i.bak 's/"channel-events"/"events:channel"/g' backend/open_webui/socket/main.py

# Verify changes
diff -u backend/open_webui/socket/main.py.bak backend/open_webui/socket/main.py
```

---

## Verification Steps

After applying changes:

```bash
# 1. Check socket/main.py changes
grep -n '"events"' backend/open_webui/socket/main.py | wc -l
# Should show: 3 (in get_event_emitter and get_event_call)

grep -n '"events:channel"' backend/open_webui/socket/main.py | wc -l
# Should show: 2 (channel events handler and emit)

# 2. Check Chat.svelte changes
grep -n "'events'" src/lib/components/chat/Chat.svelte | wc -l
# Should show: 2 (on and off listeners)

grep -n "'chat-events'" src/lib/components/chat/Chat.svelte | wc -l
# Should show: 0 (all replaced)

# 3. Verify no remaining old event names
grep -r "chat-events" backend/open_webui/ | grep -v ".bak" | wc -l
# Should show: 0

grep -r "chat-events" src/ | wc -l
# Should show: 0

# 4. Check migrations applied
cd backend && alembic current
# Should show: a5c220713937 (head)
```

---

## Testing After Changes

```bash
# 1. Start backend
cd backend
python -m open_webui.main

# In another terminal:
# 2. Start frontend
cd path/to/frontend
npm run dev

# 3. Open browser to http://localhost:5173
# 4. Check browser console (F12)
# Should see: WebSocket connection established
# Should NOT see: "Unknown event 'chat-events'"

# 5. Send a test message
# Should see real-time streaming update (not buffered)
# Should NOT see socket errors

# 6. Test token usage (if implemented)
# Should see usage data flowing through
```

---

## Rollback Instructions (If Something Goes Wrong)

```bash
# Option 1: Restore from backups
cp backend/open_webui/socket/main.py.bak backend/open_webui/socket/main.py
cp src/lib/components/chat/Chat.svelte.bak src/lib/components/chat/Chat.svelte

# Option 2: Using git
git checkout HEAD -- backend/open_webui/socket/main.py
git checkout HEAD -- src/lib/components/chat/Chat.svelte

# Option 3: Downgrade migrations
cd backend
alembic downgrade 38d63c18f30f  # Rolls back to state before user table changes

# Restart services
# Clear browser cache (Ctrl+Shift+Delete / Cmd+Shift+Delete)
# Rebuild frontend (npm run build)
```

---

## Summary of Changes

| File | Type | Old | New | Count |
|------|------|-----|-----|-------|
| socket/main.py | String | `"chat-events"` | `"events"` | 2 |
| socket/main.py | String | `"channel-events"` | `"events:channel"` | 2 |
| Chat.svelte | String | `'chat-events'` | `'events'` | 2 |
| database | Schema | N/A | Add user columns + indexes | 4 migrations |

**Total code changes: 8 string replacements + 4 database migrations**

---

## Timeline Estimate

- Manual editing: 5-10 minutes
- Running migrations: 2-5 minutes
- Testing: 10-15 minutes
- **Total: 20-30 minutes**

---

## Success Criteria

After applying patches:

- Backend logs show no "Unknown event" errors
- Frontend WebSocket connects successfully
- Chat messages stream in real-time (not chunked)
- Token usage data flows through (if implemented)
- Reasoning effort persists (if implemented)
- Database schema includes new user columns
- No TypeScript compilation errors
- No browser console errors

