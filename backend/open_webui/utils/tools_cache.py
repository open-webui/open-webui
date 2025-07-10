import json
import logging

from fastapi import Request

from open_webui.utils.tools import get_tool_servers_data

log = logging.getLogger(__name__)


REDIS_TOOL_SERVERS_KEY = "open-webui:tool_servers"


async def invalidate_tool_servers_cache(request: Request):
    """
    Invalidate tool servers cache in both Redis and memory.
    """
    request.app.state.TOOL_SERVERS = []

    # Clear Redis cache if available
    if hasattr(request.app.state, "redis") and request.app.state.redis is not None:
        try:
            await request.app.state.redis.delete(REDIS_TOOL_SERVERS_KEY)
            log.debug("Invalidated tool servers cache in Redis")
        except Exception as e:
            log.warning(f"Failed to invalidate tool servers cache in Redis: {e}")


async def get_cached_tool_servers(request: Request):
    """
    Get tool servers from Redis cache if available, otherwise from memory.
    Returns empty list if no cached data is found.
    """
    if hasattr(request.app.state, "redis") and request.app.state.redis is not None:
        try:
            cached_data = await request.app.state.redis.get(REDIS_TOOL_SERVERS_KEY)
            if cached_data:
                tool_servers = json.loads(cached_data)
                log.debug(
                    "Retrieved tool servers from Redis cache:"
                    f" {len(tool_servers)} servers"
                )
                return tool_servers
        except Exception as e:
            log.warning(f"Failed to retrieve tool servers from Redis: {e}")

    # Check in-memory cache
    if request.app.state.TOOL_SERVERS:
        # Check if all tool servers have the required _raw property. This is for backwards compatibility. before
        # we added the ability to cache tool servers in Redis. TODO: remove this some time in the future (added Jul 2025)
        if all(hasattr(server, "_raw") for server in request.app.state.TOOL_SERVERS):
            return request.app.state.TOOL_SERVERS
        else:
            log.debug("Tool servers cache missing _raw property, invalidating")
            request.app.state.TOOL_SERVERS = []

    # Check if the tool server connections have been initialized by an environment variable
    if request.app.state.config.TOOL_SERVER_CONNECTIONS:
        return await set_and_cache_tool_servers(
            request, request.app.state.config.TOOL_SERVER_CONNECTIONS
        )

    log.debug("No cached tool servers or tool server connections found")
    return []


async def set_and_cache_tool_servers(request: Request, connections: list):
    """
    Set tool server connections and immediately fetch and cache the tool servers.
    This replaces the need to store connections in app.state.config.
    """
    await invalidate_tool_servers_cache(request)

    tool_servers = await get_tool_servers_data(connections)

    request.app.state.TOOL_SERVERS = tool_servers

    # Cache in Redis if available
    if hasattr(request.app.state, "redis") and request.app.state.redis is not None:
        try:
            await request.app.state.redis.set(
                REDIS_TOOL_SERVERS_KEY,
                json.dumps(tool_servers),
                ex=300,  # 5 minutes TTL
            )
            log.debug(f"Cached tool servers in Redis: {len(tool_servers)} servers")
        except Exception as e:
            log.warning(f"Failed to cache tool servers in Redis: {e}")

    log.info(f"Fetched and cached {len(tool_servers)} tool servers")
    return tool_servers
