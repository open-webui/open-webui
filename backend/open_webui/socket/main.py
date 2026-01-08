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


if WEBSOCKET_MANAGER == "redis":
    mgr = socketio.AsyncRedisManager(WEBSOCKET_REDIS_URL)
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
        client_manager=mgr,
    )
else:
    sio = socketio.AsyncServer(
        cors_allowed_origins=[],
        async_mode="asgi",
        transports=(["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]),
        allow_upgrades=ENABLE_WEBSOCKET_SUPPORT,
        always_connect=True,
    )


# Timeout duration in seconds
TIMEOUT_DURATION = 3

# Dictionary to maintain the user pool

if WEBSOCKET_MANAGER == "redis":
    log.debug("Using Redis to manage websockets.")
    try:
        SESSION_POOL = RedisDict(
            "open-webui:session_pool", redis_url=WEBSOCKET_REDIS_URL
        )
        USER_POOL = RedisDict("open-webui:user_pool", redis_url=WEBSOCKET_REDIS_URL)
        USAGE_POOL = RedisDict("open-webui:usage_pool", redis_url=WEBSOCKET_REDIS_URL)

        clean_up_lock = RedisLock(
            redis_url=WEBSOCKET_REDIS_URL,
            lock_name="usage_cleanup_lock",
            timeout_secs=TIMEOUT_DURATION * 2,
        )
        acquire_func = clean_up_lock.acquire_lock
        renew_func = clean_up_lock.renew_lock
        release_func = clean_up_lock.release_lock
    except Exception as e:
        log.error(
            f"Failed to initialize Redis websocket manager: {e}. Falling back to local manager."
        )
        # Fallback to local management if Redis fails
        SESSION_POOL = {}
        USER_POOL = {}
        USAGE_POOL = {}
        acquire_func = release_func = renew_func = lambda: True
else:
    SESSION_POOL = {}
    USER_POOL = {}
    USAGE_POOL = {}
    acquire_func = release_func = renew_func = lambda: True


async def periodic_usage_pool_cleanup():
    """
    Periodic cleanup task for usage pool with robust error handling.
    This task should not cause application shutdown if it fails.
    """
    try:
        if not acquire_func():
            log.debug("Usage pool cleanup lock already exists. Not running it.")
            return

        log.debug("Running periodic_usage_pool_cleanup")

        while True:
            try:
                # Check if we can renew the lock
                if not renew_func():
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
            release_func()
            log.debug("Released usage pool cleanup lock")
        except Exception as e:
            log.error(f"Error releasing cleanup lock: {e}")

    log.info("Periodic usage pool cleanup task exited gracefully")


app = socketio.ASGIApp(
    sio,
    socketio_path="/ws/socket.io",
)


def get_models_in_use():
    # List models that are currently in use
    models_in_use = list(USAGE_POOL.keys())
    return models_in_use


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
            f"CrewMCP WebSocket query from user {user_session.get('id')}: {query[:100]}"
        )

        # Emit processing status
        await sio.emit(
            "crew-mcp-status",
            {"status": "processing", "message": "CrewAI is analyzing your request..."},
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

        # **ENHANCED LOGGING**
        log.info(f"crew-mcp-query: Checking for graph_access_token in session")
        log.info(
            f"crew-mcp-query: 'graph_access_token' in user_session = {('graph_access_token' in user_session)}"
        )
        log.info(f"crew-mcp-query: user_access_token type = {type(user_access_token)}")
        log.info(f"crew-mcp-query: user_access_token bool = {bool(user_access_token)}")

        if user_access_token:
            log.info(
                f"crew-mcp-query: Token found! Length={len(user_access_token)}, First 50 chars={user_access_token[:50]}"
            )
        else:
            log.warning(
                f"crew-mcp-query: NO TOKEN FOUND in session. Session has keys: {list(user_session.keys())}"
            )
            log.warning(
                f"crew-mcp-query: user_access_token value = {repr(user_access_token)}"
            )

        use_delegated_access = os.getenv(
            "SHP_USE_DELEGATED_ACCESS", "false"
        ).lower() in ("true", "1", "yes")

        log.info(f"crew-mcp-query: SHP_USE_DELEGATED_ACCESS={use_delegated_access}")

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
                    "error": "No MCP tools available. Check MCP server configuration.",
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
            result = await loop.run_in_executor(
                executor,
                crew_mcp_manager.run_intelligent_crew,
                query,
                selected_tools,
            )

        log.info(
            f"Crew execution finished via WebSocket. Result length: {len(result) if result else 0}"
        )

        used_tools = [tool["name"] for tool in tools]

        # Emit success result
        await sio.emit(
            "crew-mcp-result",
            {"result": result, "tools_used": used_tools, "success": True},
            room=sid,
        )

        log.info(f"CrewMCP WebSocket query completed successfully")

    except Exception as e:
        log.error(f"CrewMCP WebSocket error: {e}", exc_info=True)
        await sio.emit("crew-mcp-error", {"error": str(e), "code": 500}, room=sid)


@sio.event
async def connect(sid, environ, auth):
    log.info(f"WebSocket connect event: sid={sid}, auth present={bool(auth)}")
    log.info(
        f"WebSocket environ keys: {sorted([k for k in environ.keys() if k.startswith('HTTP_')])}"
    )
    user = None
    if auth and "token" in auth:
        data = decode_token(auth["token"])

        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])
            log.info(
                f"WebSocket connect: Authenticated user {user.id if user else 'None'}"
            )

        if user:
            session_data = user.model_dump()

            # Extract OAuth access token for MCP SharePoint (environ only available here during connect)
            # Import locally to avoid circular import (crew_mcp imports get_event_emitter from this module)
            try:
                from mcp_backend.routers.crew_mcp import extract_graph_access_token

                log.info(
                    "WebSocket connect: extract_graph_access_token imported successfully"
                )

                try:

                    class MinimalRequest:
                        def __init__(self, headers):
                            self.headers = headers

                    # Convert WSGI environ to headers dict
                    headers = {}
                    for key, value in environ.items():
                        if key.startswith("HTTP_"):
                            # Convert HTTP_X_FORWARDED_ACCESS_TOKEN -> x-forwarded-access-token
                            header_name = key[5:].replace("_", "-").lower()
                            headers[header_name] = value

                    log.info(
                        f"WebSocket connect: Extracted {len(headers)} HTTP headers from environ"
                    )
                    log.debug(f"WebSocket connect: Headers = {list(headers.keys())}")

                    request_obj = MinimalRequest(headers)
                    graph_access_token = extract_graph_access_token(request_obj)

                    log.info(
                        f"WebSocket connect: extract_graph_access_token returned token: {bool(graph_access_token)}"
                    )

                    if graph_access_token:
                        session_data["graph_access_token"] = graph_access_token
                        log.info(
                            f"Stored Graph access token for user {user.id} (length: {len(graph_access_token)})"
                        )
                    else:
                        log.warning(
                            f"extract_graph_access_token returned None/empty - no OAuth token found in headers"
                        )
                except Exception as e:
                    log.error(
                        f"Could not extract Graph access token: {e}", exc_info=True
                    )
            except ImportError as import_error:
                log.error(
                    f"Could not import extract_graph_access_token (circular import protection): {import_error}"
                )

            SESSION_POOL[sid] = session_data
            if user.id in USER_POOL:
                USER_POOL[user.id] = USER_POOL[user.id] + [sid]
            else:
                USER_POOL[user.id] = [sid]

            # print(f"user {user.name}({user.id}) connected with session ID {sid}")
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

    # PRESERVE the graph_access_token from the initial connect event
    existing_session = SESSION_POOL.get(sid, {})
    graph_access_token = existing_session.get("graph_access_token")

    # Update session with user data
    SESSION_POOL[sid] = user.model_dump()

    # Restore the graph_access_token if it existed
    if graph_access_token:
        SESSION_POOL[sid]["graph_access_token"] = graph_access_token
        log.info(
            f"Preserved Graph access token for user {user.id} during user-join (length: {len(graph_access_token)})"
        )

    if user.id in USER_POOL:
        USER_POOL[user.id] = USER_POOL[user.id] + [sid]
    else:
        USER_POOL[user.id] = [sid]

    # Join all the channels
    channels = Channels.get_channels_by_user_id(user.id)
    log.debug(f"{channels=}")
    for channel in channels:
        await sio.enter_room(sid, f"channel:{channel.id}")

    # print(f"user {user.name}({user.id}) connected with session ID {sid}")

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
        USER_POOL[user_id] = [_sid for _sid in USER_POOL[user_id] if _sid != sid]

        if len(USER_POOL[user_id]) == 0:
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
        group_id: The ID of the group that was updated
        group_name: The name of the group
        user_count: The new user count in the group
        action: 'added' or 'removed'
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
        f"Emitted group membership update: {action} {len(users_affected) if users_affected else 0} users to/from group '{group_name}'"
    )
