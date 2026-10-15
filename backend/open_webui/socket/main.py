import asyncio
import socketio
import logging
import sys
import time

from open_webui.models.users import Users, UserNameResponse
from open_webui.models.channels import Channels
from open_webui.models.chats import Chats

from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_URL,
)
from open_webui.utils.auth import decode_token
from open_webui.socket.utils import RedisDict, RedisLock

from open_webui.env import (
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
)

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SOCKET"])


# Timeout duration in seconds
TIMEOUT_DURATION = 3


async def _lock_noop():
    """Fallback no-op lock operation."""
    return True


def _build_socket_server(client_manager=None):
    server_kwargs = {
        "cors_allowed_origins": [],
        "async_mode": "asgi",
        "transports": (["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        "allow_upgrades": ENABLE_WEBSOCKET_SUPPORT,
        "always_connect": True,
    }
    if client_manager is not None:
        server_kwargs["client_manager"] = client_manager
    return socketio.AsyncServer(**server_kwargs)


def _initialize_socket_state():
    if WEBSOCKET_MANAGER != "redis":
        return (
            "local",
            _build_socket_server(),
            {},
            {},
            {},
            _lock_noop,
            _lock_noop,
            _lock_noop,
        )

    max_attempts = 5
    retry_delay_seconds = TIMEOUT_DURATION

    for attempt in range(1, max_attempts + 1):
        try:
            session_pool = RedisDict(
                "open-webui:session_pool", redis_url=WEBSOCKET_REDIS_URL
            )
            session_pool.redis.ping()
            user_pool = RedisDict("open-webui:user_pool", redis_url=WEBSOCKET_REDIS_URL)
            usage_pool = RedisDict(
                "open-webui:usage_pool", redis_url=WEBSOCKET_REDIS_URL
            )

            mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
            sio = _build_socket_server(client_manager=mgr)

            clean_up_lock = RedisLock(
                redis_url=WEBSOCKET_REDIS_URL,
                lock_name="usage_cleanup_lock",
                timeout_secs=TIMEOUT_DURATION * 2,
            )

            return (
                "redis",
                sio,
                session_pool,
                user_pool,
                usage_pool,
                clean_up_lock.acquire_lock,
                clean_up_lock.renew_lock,
                clean_up_lock.release_lock,
            )
        except Exception as e:
            if attempt < max_attempts:
                log.warning(
                    "Failed to initialize Redis websocket backend (attempt %s/%s): %s. Attempting to re-connect to Redis in %s seconds.",
                    attempt,
                    max_attempts,
                    e,
                    retry_delay_seconds,
                )
                time.sleep(retry_delay_seconds)
            else:
                log.error(
                    "Failed to initialize Redis websocket backend after %s attempts: %s. Aborting startup because WEBSOCKET_MANAGER is set to redis.",
                    max_attempts,
                    e,
                )
                raise RuntimeError(
                    "Redis websocket backend initialization failed while WEBSOCKET_MANAGER=redis"
                ) from e

    # Defensive guard: redis mode must never silently downgrade to local.
    raise RuntimeError(
        "Unreachable state: Redis websocket backend was not initialized while WEBSOCKET_MANAGER=redis"
    )


(
    effective_websocket_manager,
    sio,
    SESSION_POOL,
    USER_POOL,
    USAGE_POOL,
    acquire_func,
    renew_func,
    release_func,
) = _initialize_socket_state()

if effective_websocket_manager == "redis":
    log.info("Using Redis to manage websockets.")
else:
    log.warning("Using local websocket manager and local pools.")


async def periodic_usage_pool_cleanup():
    """
    Periodic cleanup task for usage pool with robust error handling.
    This task should not cause application shutdown if it fails.
    """
    try:
        if not await acquire_func():
            log.debug("Usage pool cleanup lock already exists.  Not running it.")
            return

        log.debug("Running periodic_usage_pool_cleanup")

        while True:
            try:
                # Check if we can renew the lock
                if not await renew_func():
                    log.warning(
                        "Unable to renew cleanup lock. Another instance may have taken over."
                    )
                    break

                now = int(time.time())
                send_usage = False

                try:
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

                    if send_usage:
                        # Emit updated usage information after cleaning
                        await sio.emit("usage", {"models": get_models_in_use()})

                except Exception as e:
                    log.error(f"Error during usage pool cleanup: {e}")
                    # Continue running even if cleanup fails

                await asyncio.sleep(TIMEOUT_DURATION)

            except Exception as e:
                log.error(
                    f"Error in cleanup loop: {e}. Will retry in {TIMEOUT_DURATION} seconds."
                )
                await asyncio.sleep(TIMEOUT_DURATION)
                continue

    except Exception as e:
        log.error(f"Fatal error in periodic_usage_pool_cleanup: {e}")
    finally:
        try:
            await release_func()
            log.debug("Released usage pool cleanup lock")
        except Exception as e:
            log.error(f"Error releasing cleanup lock:  {e}")

    log.info("Periodic usage pool cleanup task exited gracefully")


def flush_user_and_session_pools(prune_session_pool: bool = False):
    """
    Flush stale entries from USER_POOL and SESSION_POOL in Redis.

    The USER_POOL (keyed by user_id → list of socket SIDs) and SESSION_POOL
    (keyed by SID → user session data) can grow indefinitely because disconnected
    sessions may leave behind stale entries. This function uses live Socket.IO
    connection state as the source of truth and removes disconnected SIDs from
    USER_POOL. Optional SESSION_POOL pruning can be enabled for aggressive cleanup.

    This is designed to be called as a scheduled task to prevent unbounded memory/Redis growth and keep the "users online" list accurate.

    Returns a dict with cleanup statistics.
    """
    stats = {
        "users_before": 0,
        "users_after": 0,
        "sessions_before": 0,
        "sessions_after": 0,
        "active_sids_detected": 0,
        "stale_user_entries_removed": 0,
        "stale_sids_removed": 0,
        "orphaned_sessions_removed": 0,
        "temp_tokens_removed": 0,
    }

    try:
        sid_connection_cache = {}

        def _is_sid_connected(sid: str) -> bool:
            if sid in sid_connection_cache:
                return sid_connection_cache[sid]

            try:
                connected = bool(sio.manager.is_connected(sid, namespace="/"))
            except Exception as e:
                log.debug(
                    f"Unable to resolve Socket.IO connection state for sid={sid}: {e}"
                )
                connected = False

            sid_connection_cache[sid] = connected
            return connected

        # --- Phase 1: Clean USER_POOL using live connection state ---
        user_pool_keys = list(USER_POOL.keys())
        stats["users_before"] = len(user_pool_keys)

        for user_id in user_pool_keys:
            try:
                sids = USER_POOL.get(user_id, [])
                if not isinstance(sids, list):
                    sids = []

                active_sids = []
                seen_sids = set()
                for sid in sids:
                    if not isinstance(sid, str):
                        continue

                    if sid in seen_sids:
                        continue
                    seen_sids.add(sid)

                    if _is_sid_connected(sid):
                        active_sids.append(sid)

                removed_count = len(sids) - len(active_sids)
                stats["stale_sids_removed"] += removed_count
                # Update USER_POOL with only active SIDs for this user
                if active_sids:
                    USER_POOL[user_id] = active_sids
                else:
                    # No active sessions left for this user —> remove the user entry
                    try:
                        del USER_POOL[user_id]
                    except KeyError:
                        pass
                    stats["stale_user_entries_removed"] += 1
            except Exception as e:
                log.warning(f"Error cleaning USER_POOL entry for user {user_id}: {e}")

        stats["users_after"] = len(list(USER_POOL.keys()))
        stats["active_sids_detected"] = len(
            [sid for sid, connected in sid_connection_cache.items() if connected]
        )

        # --- Phase 2: Clean SESSION_POOL temp tokens and optionally stale sessions ---
        session_keys = list(SESSION_POOL.keys())
        stats["sessions_before"] = len(session_keys)

        for sid_key in session_keys:
            if not isinstance(sid_key, str):
                continue

            # Remove temporary token entries (prefixed with _temp_token_)
            if sid_key.startswith("_temp_token_"):
                try:
                    del SESSION_POOL[sid_key]
                    stats["temp_tokens_removed"] += 1
                except KeyError:
                    pass
                continue

            if prune_session_pool and not _is_sid_connected(sid_key):
                try:
                    del SESSION_POOL[sid_key]
                    stats["orphaned_sessions_removed"] += 1
                except KeyError:
                    pass

        stats["sessions_after"] = len(list(SESSION_POOL.keys()))

        log.info(
            f"Redis session pool cleanup completed: "
            f"USER_POOL {stats['users_before']}→{stats['users_after']} "
            f"(removed {stats['stale_user_entries_removed']} users, "
            f"{stats['stale_sids_removed']} stale SIDs), "
            f"SESSION_POOL {stats['sessions_before']}→{stats['sessions_after']} "
            f"(removed {stats['orphaned_sessions_removed']} disconnected sessions, "
            f"{stats['temp_tokens_removed']} temp tokens, "
            f"prune_session_pool={prune_session_pool})"
        )

    except Exception as e:
        log.error(f"Error during Redis session pool cleanup: {e}", exc_info=True)

    return stats


app = socketio.ASGIApp(
    sio,
    socketio_path="/ws/socket.io",
)


def get_models_in_use():
    # List models that are currently in use
    models_in_use = list(USAGE_POOL.keys())
    return models_in_use


def _remove_sid_from_user_pool(user_id: str, sid: str):
    current_sids = USER_POOL.get(user_id, [])
    if not isinstance(current_sids, list):
        current_sids = []

    remaining_sids = [_sid for _sid in current_sids if _sid != sid]
    if remaining_sids:
        USER_POOL[user_id] = remaining_sids
    elif user_id in USER_POOL:
        del USER_POOL[user_id]


def _upsert_socket_session(sid: str, session_data: dict):
    previous_session = SESSION_POOL.get(sid)
    previous_user_id = (
        previous_session.get("id") if isinstance(previous_session, dict) else None
    )
    user_id = session_data["id"]

    if previous_user_id and previous_user_id != user_id:
        _remove_sid_from_user_pool(previous_user_id, sid)

    SESSION_POOL[sid] = session_data

    current_sids = USER_POOL.get(user_id, [])
    if not isinstance(current_sids, list):
        current_sids = []

    if sid not in current_sids:
        USER_POOL[user_id] = current_sids + [sid]


@sio.on("usage")
async def usage(sid, data):
    model_id = data["model"]
    # Record the timestamp for the last update
    current_time = int(time.time())

    # Store the new usage data and task
    USAGE_POOL[model_id] = {
        **(USAGE_POOL[model_id] if model_id in USAGE_POOL else {}),
        sid: {"updated_at": current_time},
    }

    # Broadcast the usage data to all clients
    await sio.emit("usage", {"models": get_models_in_use()})


@sio.on("crew-mcp-query")
async def crew_mcp_query(sid, data):
    """Handle CrewMCP query via WebSocket"""
    try:
        # Authenticate user from session
        if sid not in SESSION_POOL:
            log.error(f"crew-mcp-query: Session {sid} not found in SESSION_POOL")
            await sio.emit(
                "crew-mcp-error",
                {"error": "Unauthorized - session not found", "code": 401},
                room=sid,
            )
            return

        user_session = SESSION_POOL[sid]
        log.info(f"crew-mcp-query: Retrieved session for sid={sid}")
        log.info(f"crew-mcp-query: Session keys: {list(user_session.keys())}")

        # Extract request data
        query = data.get("query", "")
        model = data.get("model", "")
        selected_tools = data.get("selected_tools", [])
        chat_id = data.get("chat_id", "")

        if not query:
            await sio.emit(
                "crew-mcp-error", {"error": "Query is required", "code": 400}, room=sid
            )
            return

        log.info(
            "CrewMCP WebSocket query: user=%s chat_id=%s model=%s query_len=%d tools=%d",
            user_session.get("id"),
            chat_id,
            model,
            len(query),
            len(selected_tools or []),
        )

        # Emit processing status
        await sio.emit(
            "crew-mcp-status",
            {"status": "processing", "message": "CrewAI is analyzing your request... "},
            room=sid,
        )

        # Import crew_mcp_manager
        try:
            from mcp_backend.routers.crew_mcp import crew_mcp_manager
            import os
            import asyncio
            import concurrent.futures
        except ImportError as e:
            log.error(f"Failed to import CrewMCP dependencies: {e}")
            await sio.emit(
                "crew-mcp-error",
                {"error": "CrewMCP integration not available", "code": 503},
                room=sid,
            )
            return

        # Check if manager is initialized
        if not crew_mcp_manager:
            await sio.emit(
                "crew-mcp-error",
                {"error": "CrewMCP manager not initialized", "code": 503},
                room=sid,
            )
            return

        # Get the Graph access token from session (stored during websocket connect)
        user_access_token = user_session.get("graph_access_token")

        log.info(
            "crew-mcp-query: graph_access_token present=%s", bool(user_access_token)
        )

        use_delegated_access = os.getenv(
            "SHP_USE_DELEGATED_ACCESS", "false"
        ).lower() in ("true", "1", "yes")

        log.info(f"crew-mcp-query:  SHP_USE_DELEGATED_ACCESS={use_delegated_access}")

        if use_delegated_access:
            # Delegated access (OBO flow) - use user token
            if user_access_token:
                crew_mcp_manager.set_user_token(user_access_token)
                log.info(
                    "crew-mcp-query: Set user token on crew_mcp_manager (delegated access)"
                )
            else:
                crew_mcp_manager.set_user_token(None)
                log.warning(
                    "crew-mcp-query: SHP_USE_DELEGATED_ACCESS=true but no user token available - SharePoint access may fail"
                )
        else:
            # Application access (client credentials flow) - no user token needed
            crew_mcp_manager.set_user_token(None)
            log.info(
                "crew-mcp-query: Using SharePoint application access (client credentials flow) - SHP_USE_DELEGATED_ACCESS=false"
            )

        # Get available tools
        tools = crew_mcp_manager.get_available_tools()
        if not tools:
            await sio.emit(
                "crew-mcp-error",
                {
                    "error": "No MCP tools available.  Check MCP server configuration.",
                    "code": 503,
                },
                room=sid,
            )
            return

        log.info(f"Selected tools: {selected_tools}")
        log.info("Using intelligent crew with manager agent for routing")

        # Run crew in executor to prevent blocking
        loop = asyncio.get_event_loop()
        log.info("Starting crew execution in thread pool executor via WebSocket")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            crew_result = await loop.run_in_executor(
                executor,
                crew_mcp_manager.run_intelligent_crew,
                query,
                selected_tools,
            )

        # Unpack the (result_str, token_usage, mcp_process) tuple returned by run_intelligent_crew
        if isinstance(crew_result, tuple) and len(crew_result) == 3:
            result, token_usage, mcp_process = crew_result
        else:
            result = str(crew_result)
            token_usage = {}
            mcp_process = None

        log.info(
            f"Crew execution finished via WebSocket. Result length: {len(result) if result else 0}"
        )

        # Log token consumption to message_metrics
        try:
            from open_webui.models.message_metrics import MessageMetrics
            from types import SimpleNamespace

            if token_usage and token_usage.get("total_tokens", 0) > 0:
                user_obj = SimpleNamespace(
                    id=user_session.get("id"),
                    domain=user_session.get("domain", ""),
                )
                crewai_model = (
                    f"azure/{crew_mcp_manager.azure_config.deployment}"
                    if crew_mcp_manager.azure_config.deployment
                    else "crewai"
                )
                MessageMetrics.insert_new_metrics(
                    user=user_obj,
                    model=crewai_model,
                    usage=token_usage,
                    chat_id=chat_id,
                    mcp_tool=mcp_process,
                )
        except Exception as metrics_err:
            log.warning(f"crew-mcp-query: Failed to log token metrics: {metrics_err}")

        used_tools = [tool["name"] for tool in tools]

        # Emit success result
        await sio.emit(
            "crew-mcp-result",
            {"result": result, "tools_used": used_tools, "success": True},
            room=sid,
        )

        log.info(f"CrewMCP WebSocket query completed successfully")

    except Exception as e:
        # Exception text can echo the prompt or provider payload; log the type only.
        log.error("CrewMCP WebSocket error: %s", type(e).__name__)
        await sio.emit("crew-mcp-error", {"error": str(e), "code": 500}, room=sid)


@sio.event
async def connect(sid, environ, auth):
    log.info(f"WebSocket connect event:  sid={sid}, auth present={bool(auth)}")
    log.info(
        f"WebSocket environ keys:  {sorted([k for k in environ.keys() if k.startswith('HTTP_')])}"
    )

    # Extract Graph access token from environ early and store temporarily
    graph_access_token = environ.get("HTTP_X_FORWARDED_ACCESS_TOKEN")
    if graph_access_token:
        # Store token in a temporary pool keyed by sid for later retrieval during user-join
        SESSION_POOL[f"_temp_token_{sid}"] = graph_access_token
        log.info(
            f"✅ Temporarily stored Graph access token for sid {sid} (length: {len(graph_access_token)})"
        )

    user = None

    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])
            log.info(
                f"WebSocket connect:  Authenticated user {user.id if user else 'None'}"
            )

    if user:
        session_data = user.model_dump()

        # Attach token to authenticated user session
        if graph_access_token:
            session_data["graph_access_token"] = graph_access_token
            log.info(
                f"✅ Stored Graph access token for user {user.id} (length: {len(graph_access_token)})"
            )
            # Clean up temporary storage
            if f"_temp_token_{sid}" in SESSION_POOL:
                del SESSION_POOL[f"_temp_token_{sid}"]

        _upsert_socket_session(sid, session_data)

        # Verify token was stored
        stored_session = SESSION_POOL.get(sid)
        if stored_session and "graph_access_token" in stored_session:
            log.info(
                f"✅ Verified: graph_access_token successfully stored in SESSION_POOL[{sid}]"
            )
        elif graph_access_token:
            log.error(
                f"❌ ERROR: graph_access_token NOT in SESSION_POOL after storage! This is a Redis/storage issue."
            )

        await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
        await sio.emit("usage", {"models": get_models_in_use()})


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

    # Build complete session object
    existing_session = SESSION_POOL.get(sid, {})
    graph_access_token = existing_session.get("graph_access_token")

    # Check if token was stored temporarily during connect
    temp_token_key = f"_temp_token_{sid}"
    if not graph_access_token and temp_token_key in SESSION_POOL:
        graph_access_token = SESSION_POOL[temp_token_key]
        log.info(
            f"✅ Retrieved temporarily stored Graph access token for user {user.id} during user-join (length: {len(graph_access_token)})"
        )
        # Clean up temporary storage
        del SESSION_POOL[temp_token_key]

    # Build the new session with user data
    new_session = user.model_dump()
    if graph_access_token:
        new_session["graph_access_token"] = graph_access_token
        log.info(
            f"✅ Attached Graph access token for user {user.id} during user-join (length: {len(graph_access_token)})"
        )

    # Single atomic update to Redis
    _upsert_socket_session(sid, new_session)

    # Join all the channels
    channels = Channels.get_channels_by_user_id(user.id)
    log.debug(f"{channels=}")
    for channel in channels:
        await sio.enter_room(sid, f"channel:{channel.id}")

    await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
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


@sio.on("channel-events")
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
            "channel-events",
            {
                "channel_id": data["channel_id"],
                "message_id": data.get("message_id", None),
                "data": event_data,
                "user": UserNameResponse(**SESSION_POOL[sid]).model_dump(),
            },
            room=room,
        )


@sio.on("user-list")
async def user_list(sid):
    await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})


@sio.event
async def disconnect(sid):
    if sid in SESSION_POOL:
        user = SESSION_POOL[sid]
        del SESSION_POOL[sid]

        user_id = user["id"]
        current_sids = USER_POOL.get(user_id, [])
        remaining_sids = [_sid for _sid in current_sids if _sid != sid]

        if len(remaining_sids) > 0:
            USER_POOL[user_id] = remaining_sids
        elif user_id in USER_POOL:
            del USER_POOL[user_id]

        await sio.emit("user-list", {"user_ids": list(USER_POOL.keys())})
    else:
        pass
        # print(f"Unknown session ID {sid} disconnected")


def get_event_emitter(request_info):
    async def __event_emitter__(event_data):
        user_id = request_info["user_id"]
        session_ids = list(
            set(USER_POOL.get(user_id, []) + [request_info["session_id"]])
        )

        for session_id in session_ids:
            await sio.emit(
                "chat-events",
                {
                    "chat_id": request_info["chat_id"],
                    "message_id": request_info["message_id"],
                    "data": event_data,
                },
                to=session_id,
            )

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

    return __event_emitter__


def get_event_call(request_info):
    async def __event_call__(event_data):
        response = await sio.call(
            "chat-events",
            {
                "chat_id": request_info["chat_id"],
                "message_id": request_info["message_id"],
                "data": event_data,
            },
            to=request_info["session_id"],
        )
        return response

    return __event_call__


def get_user_id_from_session_pool(sid):
    user = SESSION_POOL.get(sid)
    if user:
        return user["id"]
    return None


def get_user_ids_from_room(room):
    active_session_ids = sio.manager.get_participants(
        namespace="/",
        room=room,
    )

    active_user_ids = list(
        set(
            [SESSION_POOL.get(session_id[0])["id"] for session_id in active_session_ids]
        )
    )
    return active_user_ids


def get_active_status_by_user_id(user_id):
    if user_id in USER_POOL:
        return True
    return False


async def emit_group_membership_update(
    group_id: str,
    group_name: str,
    user_count: int,
    action: str,
    users_affected: list = None,
):
    """
    Emit group membership changes to all connected clients

    Args:
        group_id:  The ID of the group that was updated
        group_name: The name of the group
        user_count: The new user count in the group
        action:  'added' or 'removed'
        users_affected: List of user emails or IDs that were affected (optional)
    """
    event_data = {
        "group_id": group_id,
        "group_name": group_name,
        "user_count": user_count,
        "action": action,
        "timestamp": int(time.time()),
    }

    if users_affected:
        event_data["users_affected"] = users_affected
        event_data["users_count"] = len(users_affected)

    # Emit to all connected clients
    await sio.emit("group-membership-update", event_data)
    log.info(
        f"Emitted group membership update:  {action} {len(users_affected) if users_affected else 0} users to/from group '{group_name}'"
    )
