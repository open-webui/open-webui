# Quick Reference: Critical Changes to Apply

## TL;DR - Critical Changes in 3 Files

### 1. Backend Socket Events (CRITICAL)
**File:** `/backend/open_webui/socket/main.py`

Replace these 7 occurrences:
```diff
- sio.emit("chat-events", ...)
+ sio.emit("events", ...)

- sio.emit("channel-events", ...)
+ sio.emit("events:channel", ...)

- sio.call("chat-events", ...)
+ sio.call("events", ...)
```

Line numbers in your fork:
- Line 718: `emit_tasks` - "chat-events" → "events"
- Line 739: Another `sio.emit("chat-events"` → "events"

### 2. Frontend Socket Listener (CRITICAL)
**File:** `/src/lib/components/chat/Chat.svelte`

Replace 2 occurrences:
```diff
- $socket?.on('chat-events', chatEventHandler);
+ $socket?.on('events', chatEventHandler);

- $socket?.off('chat-events', chatEventHandler);
+ $socket?.off('events', chatEventHandler);
```

Line numbers in your fork:
- Line 514: `$socket?.on('chat-events'...`
- Line 588: `$socket?.off('chat-events'...`

### 3. Apply 4 Database Migrations (IMPORTANT)

Run these Alembic migrations **before** your custom token migration:

```bash
cd backend

# From commit 5fbfe2bdc to upstream/main, apply:
alembic upgrade 018012973d35  # add_indexes
alembic upgrade 38d63c18f30f  # add_oauth_session_table
alembic upgrade 3af16a1c9fb6  # update_user_table (ADDS: username, bio, gender, date_of_birth)
alembic upgrade a5c220713937  # add_reply_to_id_column_to_message
```

**Critical:** Your token migration must come AFTER `3af16a1c9fb6_update_user_table.py`

---

## File Changes Summary

| File | Change Type | Details | Lines |
|------|-------------|---------|-------|
| `backend/open_webui/socket/main.py` | Event name refactor | `chat-events` → `events` | 718, 739, 773 |
| `backend/open_webui/socket/main.py` | Event name refactor | `channel-events` → `events:channel` | 359 |
| `src/lib/components/chat/Chat.svelte` | Event listener | `chat-events` → `events` | 514, 588 |
| `backend/open_webui/models/users.py` | Add columns (via migration) | username, bio, gender, date_of_birth | - |
| `backend/open_webui/utils/middleware.py` | Enhancement | New stream_delta_chunk_size param | 952 |
| `src/lib/components/chat/MessageInput.svelte` | Refactor | Integrate with new component structure | - |

---

## Affected Custom Features

### Token Usage Tracking ✓ (MOSTLY OK)
- **Impact:** Low - Your system is architecture-compatible
- **Action:** Update socket event names above
- **Note:** Migration order matters for database schema

### Reasoning Effort Selection ✓ (NEEDS INTEGRATION)
- **Impact:** Medium - Component refactored, feature not in upstream
- **Action:** Manually integrate reasoning effort UI with new MessageInput
- **Note:** Your payload structure remains compatible

### Live Usage Display ❌ (WILL BREAK)
- **Impact:** CRITICAL - WebSocket event name changed
- **Action:** Update socket listeners to use `'events'` instead of `'chat-events'`
- **Note:** Must update both backend and frontend

---

## Upstream Migration Details

**User Table Migration: 3af16a1c9fb6**
```sql
ALTER TABLE user ADD COLUMN username VARCHAR(50);
ALTER TABLE user ADD COLUMN bio TEXT;
ALTER TABLE user ADD COLUMN gender TEXT;
ALTER TABLE user ADD COLUMN date_of_birth DATE;
```

**Message Table Migration: a5c220713937**
```sql
ALTER TABLE message ADD COLUMN reply_to_id VARCHAR;
```

**OAuth Session Table: 38d63c18f30f**
```sql
CREATE TABLE oauth_session (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    provider VARCHAR,
    access_token TEXT,
    created_at BIGINT,
    ...
);
```

**Indexes: 018012973d35**
- Adds performance indexes on frequently queried columns

---

## Testing After Changes

Quick verification:
1. Backend starts: `python -m open_webui.main`
2. Frontend compiles: `npm run build`
3. Socket connects: Check browser console for no WebSocket errors
4. Chat works: Send a message, verify real-time streaming
5. Token usage: Verify tracking still functions (if implemented)
6. Reasoning effort: Verify localStorage persistence (if implemented)

---

## Common Errors & Fixes

### Error: "Unknown event 'chat-events'"
**Cause:** Missed updating socket listener
**Fix:** Verify all 7 event name changes above are applied

### Error: "chat_events" column not found
**Cause:** Missing database migrations
**Fix:** Run all 4 upstream migrations in order

### Error: TypeError: Cannot read property 'emit' of undefined
**Cause:** Socket not initialized
**Fix:** Verify socket connection in root layout

### Error: "user.bio is undefined"
**Cause:** Migration applied but frontend code didn't update
**Fix:** Clear browser cache, rebuild frontend

---

## Files to Check for Additional Socket Listeners

Search your entire codebase for old socket event names:

```bash
# Find any remaining references to old event names
grep -r "chat-events" src/
grep -r "'chat-events'" src/
grep -r '"chat-events"' src/
grep -r "channel-events" src/
```

---

## Rollback Plan (If Something Breaks)

1. **Revert socket changes:** Use git to revert socket/main.py changes
2. **Downgrade migrations:** `alembic downgrade <previous_revision>`
3. **Restore from backup:** Use your pre-migration database backup
4. **Restart services:** Clear caches and restart backend/frontend

---

## New Upstream Features (Optional Nice-to-Haves)

These don't break existing code but add useful functionality:

1. **Message Threading** - Use `reply_to_id` in messages
2. **OAuth Session Storage** - Better OAuth token management
3. **User Profiles** - Bio, gender, date of birth display
4. **Template Variables** - `{{USER_AGE}}`, `{{USER_BIO}}`, etc.

---

## Support & Debugging

If changes don't work:

1. **Check git diff:** Verify changes match expected lines
2. **Check migrations:** `alembic current` shows current revision
3. **Check logs:** Backend logs show socket event emissions
4. **Check browser console:** Frontend shows socket listener registration
5. **Check database:** Verify new columns exist after migration

---

## Next Steps

1. **Backup database** (CRITICAL)
2. **Apply socket event name changes** (2 files, 7 places)
3. **Run database migrations** (4 files, in order)
4. **Test WebSocket connection** (check browser console)
5. **Verify features still work** (chat, token usage, reasoning effort)
6. **Deploy to production** (after local testing)

