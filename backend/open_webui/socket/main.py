import asyncio
import random

import socketio
import logging
import sys
import time
from typing import Dict, Set
from redis import asyncio as aioredis
import pycrdt as Y

from open_webui.models.users import Users, UserNameResponse
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats
from open_webui.models.notes import Notes, NoteUpdateForm
from open_webui.utils.redis import (
    get_sentinels_from_env,
    get_sentinel_url_from_env,
)

from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_URL,
    WEBSOCKET_REDIS_CLUSTER,
    WEBSOCKET_REDIS_LOCK_TIMEOUT,
    WEBSOCKET_SENTINEL_PORT,
    WEBSOCKET_SENTINEL_HOSTS,
    WEBSOCKET_MAX_MESSAGE_SIZE,
    REDIS_KEY_PREFIX,
)
from open_webui.utils.auth import decode_token
from open_webui.socket.utils import RedisDict, RedisLock, YdocManager
from open_webui.tasks import create_task, stop_item_tasks, set_pending_model_switch, list_task_ids_by_item_id
from open_webui.utils.redis import get_redis_connection
from open_webui.utils.access_control import has_access, get_users_with_access
from open_webui.models.token_usage import token_groups


from open_webui.env import (
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
)


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SOCKET"])


REDIS = None

if WEBSOCKET_MANAGER == "redis":
    if WEBSOCKET_SENTINEL_HOSTS:
        mgr = socketio.AsyncRedisManager(
            get_sentinel_url_from_env(
                WEBSOCKET_REDIS_URL, WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
            )
        )
    else:
        mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=mgr,
        max_http_buffer_size=WEBSOCKET_MAX_MESSAGE_SIZE,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        max_http_buffer_size=WEBSOCKET_MAX_MESSAGE_SIZE,
    )


# Timeout duration in seconds
TIMEOUT_DURATION = 3

# Dictionary to maintain the user pool

if WEBSOCKET_MANAGER == "redis":
    log.debug("Using Redis to manage websockets.")
    REDIS = get_redis_connection(
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=get_sentinels_from_env(
            WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
        ),
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        async_mode=True,
    )

    redis_sentinels = get_sentinels_from_env(
        WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT
    )
    SESSION_POOL = RedisDict(
        f"{REDIS_KEY_PREFIX}:session_pool",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    USER_POOL = RedisDict(
        f"{REDIS_KEY_PREFIX}:user_pool",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    USAGE_POOL = RedisDict(
        f"{REDIS_KEY_PREFIX}:usage_pool",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )

    # Token usage tracking data structures
    TOKEN_GROUPS = RedisDict(
        "open-webui:token_groups",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
    )
    TOKEN_USAGE = RedisDict(
        "open-webui:token_usage",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=redis_sentinels,
    )

    clean_up_lock = RedisLock(
        redis_url=WEBSOCKET_REDIS_URL,
        lock_name=f"{REDIS_KEY_PREFIX}:usage_cleanup_lock",
        timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
        redis_sentinels=redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
    aquire_func = clean_up_lock.aquire_lock
    renew_func = clean_up_lock.renew_lock
    release_func = clean_up_lock.release_lock
else:
    SESSION_POOL = {}
    USER_POOL = {}
    USAGE_POOL = {}

    # Token usage tracking data structures (in-memory)
    TOKEN_GROUPS = {}
    TOKEN_USAGE = {}

    aquire_func = release_func = renew_func = lambda: True


YDOC_MANAGER = YdocManager(
    redis=REDIS,
    redis_key_prefix=f"{REDIS_KEY_PREFIX}:ydoc:documents",
)


async def periodic_usage_pool_cleanup():
    max_retries = 2
    retry_delay = random.uniform(
        WEBSOCKET_REDIS_LOCK_TIMEOUT / 2, WEBSOCKET_REDIS_LOCK_TIMEOUT
    )
    for attempt in range(max_retries + 1):
        if aquire_func():
            break
        else:
            if attempt < max_retries:
                log.debug(
                    f"Cleanup lock already exists. Retry {attempt + 1} after {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
            else:
                log.warning(
                    "Failed to acquire cleanup lock after retries. Skipping cleanup."
                )
                return

    log.debug("Running periodic_cleanup")
    try:
        while True:
            if not renew_func():
                log.error(f"Unable to renew cleanup lock. Exiting usage pool cleanup.")
                raise Exception("Unable to renew usage pool cleanup lock.")

            now = int(time.time())
            send_usage = False
            for model_id, connections in list(USAGE_POOL.items()):
                # Creating a list of sids to remove if they have timed out
                expired_sids = [
                    sid
                    for sid, details in connections.items()
                    if now - details["updated_at"] > TIMEOUT_DURATION
                ]

                for sid in expired_sids:
                    del connections[sid]

                if not connections:
                    log.debug(f"Cleaning up model {model_id} from usage pool")
                    del USAGE_POOL[model_id]
                else:
                    USAGE_POOL[model_id] = connections

                send_usage = True
            await asyncio.sleep(TIMEOUT_DURATION)
    finally:
        release_func()


app = socketio.ASGIApp(
    sio,
    socketio_path="/ws/socket.io",
)


def get_models_in_use():
    # List models that are currently in use
    models_in_use = list(USAGE_POOL.keys())
    return models_in_use


def get_active_user_ids():
    """Get the list of active user IDs."""
    return list(USER_POOL.keys())


def get_user_active_status(user_id):
    """Check if a user is currently active."""
    return user_id in USER_POOL


def get_user_id_from_session_pool(sid):
    user = SESSION_POOL.get(sid)
    if user:
        return user["id"]
    return None


def get_session_ids_from_room(room):
    """Get all session IDs from a specific room."""
    active_session_ids = sio.manager.get_participants(
        namespace="/",
        room=room,
    )
    return [session_id[0] for session_id in active_session_ids]


def get_user_ids_from_room(room):
    active_session_ids = get_session_ids_from_room(room)

    active_user_ids = list(
        set([SESSION_POOL.get(session_id)["id"] for session_id in active_session_ids])
    )
    return active_user_ids


def get_active_status_by_user_id(user_id):
    if user_id in USER_POOL:
        return True
    return False


def get_token_groups():
    """Get all token groups"""
    return token_groups.get_token_groups()


def set_token_group(group_name: str, models: list, limit: int = None, reset_time: str = '00:00', reset_timezone: str = 'UTC', window_duration: int = None):
    """Set a token group"""
    # Try to update first, if not found create new
    if not token_groups.update_token_group(group_name, models, limit, window_duration):
        return token_groups.create_token_group(group_name, models, limit or 0, reset_time, reset_timezone, window_duration)


def update_token_group(group_name: str, models: list = None, limit: int = None, window_duration: int = None):
    """Update an existing token group"""
    return token_groups.update_token_group(group_name, models, limit, window_duration)


def delete_token_group(group_name: str):
    """Delete a token group"""
    return token_groups.delete_token_group(group_name)


def get_token_usage():
    """Get current token usage for all groups from database"""
    # Import here to avoid circular imports
    from open_webui.models.token_usage import token_groups as db_token_groups
    groups = db_token_groups.get_token_groups()  # This returns groups WITH usage from DB
    return {name: group_data["usage"] for name, group_data in groups.items()}


@sio.on("usage")
async def usage(sid, data):
    if sid in SESSION_POOL:
        model_id = data["model"]
        usage_data = data.get("usage", {})
        
        # Get user_id from session pool and chat_id from data
        user = SESSION_POOL.get(sid)
        user_id = user.get("id") if user else None
        chat_id = data.get("chat_id")
        
        log.info(f"📊 [socket:usage] Received from frontend: model={model_id}, chat_id={chat_id}, user_id={user_id}")

        # Record the timestamp for the last update
        current_time = int(time.time())

        # Store the new usage data and task
        USAGE_POOL[model_id] = {
            **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
            sid: {"updated_at": current_time},
        }

        # Process token usage tracking with chat_id and user_id for analytics
        await process_token_usage(model_id, usage_data, chat_id=chat_id, user_id=user_id)


@sio.on("model-switch")
async def model_switch(sid, data):
    """
    Handle model switch requests during an active agentic loop.
    The switch will be applied at the next iteration of the tool call loop.
    """
    if sid not in SESSION_POOL:
        return {"status": False, "message": "Session not found"}
    
    chat_id = data.get("chat_id")
    new_model_id = data.get("model_id")
    task_id = data.get("task_id")
    
    if not new_model_id:
        return {"status": False, "message": "No model_id provided"}
    
    log.info(f"Model switch request: chat_id={chat_id}, task_id={task_id}, new_model={new_model_id}")
    
    # If a specific task_id is provided, switch for that task
    if task_id:
        result = await set_pending_model_switch(task_id, new_model_id)
        
        # Emit event to notify frontend that model switch is pending
        await sio.emit(
            "events",
            {
                "chat_id": chat_id,
                "message_id": data.get("message_id"),
                "data": {
                    "type": "model-switch:pending",
                    "data": {
                        "task_id": task_id,
                        "model_id": new_model_id,
                    }
                }
            },
            to=sid,
        )
        
        return result
    
    # If no task_id provided, try to find active tasks for the chat
    if chat_id:
        task_ids = await list_task_ids_by_item_id(REDIS, chat_id)
        if task_ids:
            results = []
            for tid in task_ids:
                result = await set_pending_model_switch(tid, new_model_id)
                results.append(result)
            
            # Emit event for each task
            await sio.emit(
                "events",
                {
                    "chat_id": chat_id,
                    "message_id": data.get("message_id"),
                    "data": {
                        "type": "model-switch:pending",
                        "data": {
                            "task_ids": task_ids,
                            "model_id": new_model_id,
                        }
                    }
                },
                to=sid,
            )
            
            return {"status": True, "message": f"Model switch queued for {len(task_ids)} active task(s)"}
        else:
            return {"status": False, "message": "No active tasks found for this chat"}
    
    return {"status": False, "message": "No chat_id or task_id provided"}


async def process_token_usage(
    model_id: str,
    usage_data: dict,
    chat_id: str = None,
    user_id: str = None
):
    """
    Process token usage data and update all tracking tables.
    
    Updates:
    1. Token group usage (existing rate limiting feature)
    2. Conversation token usage (new - for per-chat tracking)
    3. Daily token usage (new - for heatmaps)
    4. Model token usage (new - for model breakdowns)
    
    Args:
        model_id: The model being used
        usage_data: Dict containing prompt_tokens, completion_tokens, etc.
        chat_id: Optional chat ID for conversation tracking
        user_id: Optional user ID for user-level analytics
    """
    log.info(f"📊 [process_token_usage] Called with model={model_id}, chat_id={chat_id}, user_id={user_id}")
    log.info(f"📊 [process_token_usage] usage_data={usage_data}")
    
    if not usage_data:
        log.info(f"📊 [process_token_usage] No usage_data, returning early")
        return

    # Extract token counts with safe defaults
    prompt_tokens = usage_data.get("prompt_tokens", 0)
    completion_tokens = usage_data.get("completion_tokens", 0)

    # Extract reasoning tokens from completion_tokens_details
    completion_tokens_details = usage_data.get("completion_tokens_details", {}) or {}
    reasoning_tokens = completion_tokens_details.get("reasoning_tokens", 0)

    # Calculate IN, OUT, TOTAL according to spec
    # IN = prompt_tokens
    # OUT = completion_tokens + reasoning_tokens
    # TOTAL = IN + OUT
    token_in = prompt_tokens
    token_out = completion_tokens + reasoning_tokens
    token_total = token_in + token_out
    
    log.info(f"📊 [process_token_usage] Calculated: in={token_in}, out={token_out}, total={token_total}")

    # 1. Update existing group-based token tracking (for rate limiting)
    token_groups.update_token_usage(model_id, token_in, token_out, token_total)

    # 2-4. Update analytics tables for "Wrapped" feature
    try:
        from open_webui.models.analytics import Analytics
        
        # 2. Update conversation token usage (per-chat tracking)
        if chat_id and user_id:
            log.info(f"📊 [process_token_usage] Updating conversation token usage for chat={chat_id}, user={user_id}")
            result = Analytics.update_conversation_token_usage(
                chat_id=chat_id,
                user_id=user_id,
                model_id=model_id,
                token_in=token_in,
                token_out=token_out,
                token_total=token_total
            )
            log.info(f"📊 [process_token_usage] Conversation update result: {result}")
        else:
            log.info(f"📊 [process_token_usage] Skipping conversation update - chat_id={chat_id}, user_id={user_id}")
        
        # 3. Update daily token usage (for heatmaps)
        if user_id:
            log.info(f"📊 [process_token_usage] Updating daily token usage for user={user_id}")
            Analytics.update_daily_token_usage(
                user_id=user_id,
                token_in=token_in,
                token_out=token_out,
                token_total=token_total,
                chat_id=chat_id
            )
        
        # 4. Update model token usage (for model breakdowns)
        log.info(f"📊 [process_token_usage] Updating model token usage for model={model_id}")
        Analytics.update_model_token_usage(
            user_id=user_id,
            model_id=model_id,
            token_in=token_in,
            token_out=token_out,
            token_total=token_total
        )
        
        log.info(f"📊 [process_token_usage] SUCCESS: model={model_id}, chat={chat_id}, user={user_id}, tokens={token_total}")
    except Exception as e:
        log.error(f"📊 [process_token_usage] ERROR updating analytics: {e}", exc_info=True)


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user:
            SESSION_POOL[sid] = user.model_dump(
                exclude=["date_of_birth", "bio", "gender"]
            )
            if user.id in USER_POOL:
                USER_POOL[user.id] = USER_POOL[user.id] + [sid]
            else:
                USER_POOL[user.id] = [sid]


@sio.on("user-join")
async def user_join(sid, data):

    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    SESSION_POOL[sid] = user.model_dump(exclude=["date_of_birth", "bio", "gender"])
    if user.id in USER_POOL:
        USER_POOL[user.id] = USER_POOL[user.id] + [sid]
    else:
        USER_POOL[user.id] = [sid]

    # Join all the channels
    channels = Channels.get_channels_by_user_id(user.id)
    log.debug(f"{channels=}")
    for channel in channels:
        await sio.enter_room(sid, f"channel:{channel.id}")
    return {"id": user.id, "name": user.name}


@sio.on("join-channels")
async def join_channel(sid, data):
    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    data = decode_token(auth["token"])
    if data is None or "id" not in data:
        return

    user = Users.get_user_by_id(data["id"])
    if not user:
        return

    # Join all the channels
    channels = Channels.get_channels_by_user_id(user.id)
    log.debug(f"{channels=}")
    for channel in channels:
        await sio.enter_room(sid, f"channel:{channel.id}")


@sio.on("join-note")
async def join_note(sid, data):
    auth = data["auth"] if "auth" in data else None
    if not auth or "token" not in auth:
        return

    token_data = decode_token(auth["token"])
    if token_data is None or "id" not in token_data:
        return

    user = Users.get_user_by_id(token_data["id"])
    if not user:
        return

    note = Notes.get_note_by_id(data["note_id"])
    if not note:
        log.error(f"Note {data['note_id']} not found for user {user.id}")
        return

    if (
        user.role != "admin"
        and user.id != note.user_id
        and not has_access(user.id, type="read", access_control=note.access_control)
    ):
        log.error(f"User {user.id} does not have access to note {data['note_id']}")
        return

    log.debug(f"Joining note {note.id} for user {user.id}")
    await sio.enter_room(sid, f"note:{note.id}")


@sio.on("events:channel")
async def channel_events(sid, data):
    room = f"channel:{data['channel_id']}"
    participants = sio.manager.get_participants(
        namespace="/",
        room=room,
    )

    sids = [sid for sid, _ in participants]
    if sid not in sids:
        return

    event_data = data["data"]
    event_type = event_data["type"]

    if event_type == "typing":
        await sio.emit(
            "events:channel",
            {
                "channel_id": data["channel_id"],
                "message_id": data.get("message_id", None),
                "data": event_data,
                "user": UserNameResponse(**SESSION_POOL[sid]).model_dump(),
            },
            room=room,
        )


@sio.on("ydoc:document:join")
async def ydoc_document_join(sid, data):
    """Handle user joining a document"""
    user = SESSION_POOL.get(sid)

    try:
        document_id = data["document_id"]

        if document_id.startswith("note:"):
            note_id = document_id.split(":")[1]
            note = Notes.get_note_by_id(note_id)
            if not note:
                log.error(f"Note {note_id} not found")
                return

            if (
                user.get("role") != "admin"
                and user.get("id") != note.user_id
                and not has_access(
                    user.get("id"), type="read", access_control=note.access_control
                )
            ):
                log.error(
                    f"User {user.get('id')} does not have access to note {note_id}"
                )
                return

        user_id = data.get("user_id", sid)
        user_name = data.get("user_name", "Anonymous")
        user_color = data.get("user_color", "#000000")

        log.info(f"User {user_id} joining document {document_id}")
        await YDOC_MANAGER.add_user(document_id=document_id, user_id=sid)

        # Join Socket.IO room
        await sio.enter_room(sid, f"doc_{document_id}")

        active_session_ids = get_session_ids_from_room(f"doc_{document_id}")

        # Get the Yjs document state
        ydoc = Y.Doc()
        updates = await YDOC_MANAGER.get_updates(document_id)
        for update in updates:
            ydoc.apply_update(bytes(update))

        # Encode the entire document state as an update
        state_update = ydoc.get_update()
        await sio.emit(
            "ydoc:document:state",
            {
                "document_id": document_id,
                "state": list(state_update),  # Convert bytes to list for JSON
                "sessions": active_session_ids,
            },
            room=sid,
        )

        # Notify other users about the new user
        await sio.emit(
            "ydoc:user:joined",
            {
                "document_id": document_id,
                "user_id": user_id,
                "user_name": user_name,
                "user_color": user_color,
            },
            room=f"doc_{document_id}",
            skip_sid=sid,
        )

        log.info(f"User {user_id} successfully joined document {document_id}")

    except Exception as e:
        log.error(f"Error in yjs_document_join: {e}")
        await sio.emit("error", {"message": "Failed to join document"}, room=sid)


async def document_save_handler(document_id, data, user):
    if document_id.startswith("note:"):
        note_id = document_id.split(":")[1]
        note = Notes.get_note_by_id(note_id)
        if not note:
            log.error(f"Note {note_id} not found")
            return

        if (
            user.get("role") != "admin"
            and user.get("id") != note.user_id
            and not has_access(
                user.get("id"), type="read", access_control=note.access_control
            )
        ):
            log.error(f"User {user.get('id')} does not have access to note {note_id}")
            return

        Notes.update_note_by_id(note_id, NoteUpdateForm(data=data))


@sio.on("ydoc:document:state")
async def yjs_document_state(sid, data):
    """Send the current state of the Yjs document to the user"""
    try:
        document_id = data["document_id"]
        room = f"doc_{document_id}"

        active_session_ids = get_session_ids_from_room(room)

        if sid not in active_session_ids:
            log.warning(f"Session {sid} not in room {room}. Cannot send state.")
            return

        if not await YDOC_MANAGER.document_exists(document_id):
            log.warning(f"Document {document_id} not found")
            return

        # Get the Yjs document state
        ydoc = Y.Doc()
        updates = await YDOC_MANAGER.get_updates(document_id)
        for update in updates:
            ydoc.apply_update(bytes(update))

        # Encode the entire document state as an update
        state_update = ydoc.get_update()

        await sio.emit(
            "ydoc:document:state",
            {
                "document_id": document_id,
                "state": list(state_update),  # Convert bytes to list for JSON
                "sessions": active_session_ids,
            },
            room=sid,
        )
    except Exception as e:
        log.error(f"Error in yjs_document_state: {e}")


@sio.on("ydoc:document:update")
async def yjs_document_update(sid, data):
    """Handle Yjs document updates"""
    try:
        document_id = data["document_id"]

        try:
            await stop_item_tasks(REDIS, document_id)
        except:
            pass

        user_id = data.get("user_id", sid)

        update = data["update"]  # List of bytes from frontend

        await YDOC_MANAGER.append_to_updates(
            document_id=document_id,
            update=update,  # Convert list of bytes to bytes
        )

        # Broadcast update to all other users in the document
        await sio.emit(
            "ydoc:document:update",
            {
                "document_id": document_id,
                "user_id": user_id,
                "update": update,
                "socket_id": sid,  # Add socket_id to match frontend filtering
            },
            room=f"doc_{document_id}",
            skip_sid=sid,
        )

        async def debounced_save():
            await asyncio.sleep(0.5)
            await document_save_handler(
                document_id, data.get("data", {}), SESSION_POOL.get(sid)
            )

        if data.get("data"):
            await create_task(REDIS, debounced_save(), document_id)

    except Exception as e:
        log.error(f"Error in yjs_document_update: {e}")


@sio.on("ydoc:document:leave")
async def yjs_document_leave(sid, data):
    """Handle user leaving a document"""
    try:
        document_id = data["document_id"]
        user_id = data.get("user_id", sid)

        log.info(f"User {user_id} leaving document {document_id}")

        # Remove user from the document
        await YDOC_MANAGER.remove_user(document_id=document_id, user_id=sid)

        # Leave Socket.IO room
        await sio.leave_room(sid, f"doc_{document_id}")

        # Notify other users
        await sio.emit(
            "ydoc:user:left",
            {"document_id": document_id, "user_id": user_id},
            room=f"doc_{document_id}",
        )

        if (
            await YDOC_MANAGER.document_exists(document_id)
            and len(await YDOC_MANAGER.get_users(document_id)) == 0
        ):
            log.info(f"Cleaning up document {document_id} as no users are left")
            await YDOC_MANAGER.clear_document(document_id)

    except Exception as e:
        log.error(f"Error in yjs_document_leave: {e}")


@sio.on("ydoc:awareness:update")
async def yjs_awareness_update(sid, data):
    """Handle awareness updates (cursors, selections, etc.)"""
    try:
        document_id = data["document_id"]
        user_id = data.get("user_id", sid)
        update = data["update"]

        # Broadcast awareness update to all other users in the document
        await sio.emit(
            "ydoc:awareness:update",
            {"document_id": document_id, "user_id": user_id, "update": update},
            room=f"doc_{document_id}",
            skip_sid=sid,
        )

    except Exception as e:
        log.error(f"Error in yjs_awareness_update: {e}")


@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        user = SESSION_POOL[sid]
        del SESSION_POOL[sid]

        user_id = user["id"]
        USER_POOL[user_id] = [_sid for _sid in USER_POOL[user_id] if _sid != sid]

        if len(USER_POOL[user_id]) == 0:
            del USER_POOL[user_id]

        await YDOC_MANAGER.remove_user_from_all_documents(sid)
    else:
        pass
        # print(f"Unknown session ID {sid} disconnected")


def get_event_emitter(request_info, update_db=True):
    async def __event_emitter__(event_data):
        user_id = request_info["user_id"]

        session_ids = list(
            set(
                USER_POOL.get(user_id, [])
                + (
                    [request_info.get("session_id")]
                    if request_info.get("session_id")
                    else []
                )
            )
        )

        chat_id = request_info.get("chat_id", None)
        message_id = request_info.get("message_id", None)

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

        await asyncio.gather(*emit_tasks)
        if (
            update_db
            and message_id
            and not request_info.get("chat_id", "").startswith("local:")
        ):
            if "type" in event_data and event_data["type"] == "status":
                Chats.add_message_status_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    event_data.get("data", {}),
                )

            if "type" in event_data and event_data["type"] == "message":
                message = Chats.get_message_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                )

                if message:
                    content = message.get("content", "")
                    content += event_data.get("data", {}).get("content", "")

                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        request_info["chat_id"],
                        request_info["message_id"],
                        {
                            "content": content,
                        },
                    )

            if "type" in event_data and event_data["type"] == "replace":
                content = event_data.get("data", {}).get("content", "")

                Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    {
                        "content": content,
                    },
                )

            if "type" in event_data and event_data["type"] == "embeds":
                message = Chats.get_message_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                )

                embeds = event_data.get("data", {}).get("embeds", [])
                embeds.extend(message.get("embeds", []))

                Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    {
                        "embeds": embeds,
                    },
                )

            if "type" in event_data and event_data["type"] == "files":
                message = Chats.get_message_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                )

                files = event_data.get("data", {}).get("files", [])
                files.extend(message.get("files", []))

                Chats.upsert_message_to_chat_by_id_and_message_id(
                    request_info["chat_id"],
                    request_info["message_id"],
                    {
                        "files": files,
                    },
                )

            if event_data.get("type") in ["source", "citation"]:
                data = event_data.get("data", {})
                if data.get("type") == None:
                    message = Chats.get_message_by_id_and_message_id(
                        request_info["chat_id"],
                        request_info["message_id"],
                    )

                    sources = message.get("sources", [])
                    sources.append(data)

                    Chats.upsert_message_to_chat_by_id_and_message_id(
                        request_info["chat_id"],
                        request_info["message_id"],
                        {
                            "sources": sources,
                        },
                    )

    return __event_emitter__


def get_event_call(request_info):
    async def __event_caller__(event_data):
        try:
            response = await sio.call(
                "events",
                {
                    "chat_id": request_info.get("chat_id", None),
                    "message_id": request_info.get("message_id", None),
                    "data": event_data,
                },
                to=request_info["session_id"],
            )
            return response
        except Exception as e:
            log.error(f"Error calling socket event: {e}", exc_info=True)
            return {"status": False, "error": str(e)}

    return __event_caller__


get_event_caller = get_event_call
