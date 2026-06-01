"""Redis connection utilities.

Provides connection factory functions for standalone, Sentinel, and Cluster
Redis deployments, with optional async support and automatic connection caching.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any
from urllib.parse import ParseResult, urlparse

import redis as _redis_sync

from open_webui.env import (
    REDIS_CLUSTER,
    REDIS_HEALTH_CHECK_INTERVAL,
    REDIS_RECONNECT_DELAY,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_MAX_RETRY_COUNT,
    REDIS_SENTINEL_PORT,
    REDIS_SOCKET_CONNECT_TIMEOUT,
    REDIS_SOCKET_KEEPALIVE,
    REDIS_URL,
)

log = logging.getLogger(__name__)

_ACCEPTED_SCHEMES = frozenset({"redis", "rediss"})
_SENTINEL_RETRYABLE = (
    _redis_sync.exceptions.ConnectionError,
    _redis_sync.exceptions.ReadOnlyError,
)
_FACTORY_METHODS = frozenset({"pipeline", "pubsub", "monitor", "client", "transaction"})
_CONNECTION_POOL: dict[tuple, Any] = {}


def parse_redis_url(url: str) -> dict[str, Any]:
    """Break a ``redis://`` URL into its parts: service, port, db, username, password."""
    parts: ParseResult = urlparse(url)
    if parts.scheme not in _ACCEPTED_SCHEMES:
        raise ValueError(
            f"Invalid Redis URL scheme '{parts.scheme}'; expected 'redis' or 'rediss'."
        )
    return {
        "service": parts.hostname or "mymaster",
        "port": parts.port or 6379,
        "db": int(parts.path.lstrip("/") or "0"),
        "username": parts.username or None,
        "password": parts.password or None,
    }

parse_redis_service_url = parse_redis_url


def get_sentinels_from_env(
    hosts_csv: str | None,
    port: str | int | None,
) -> list[tuple[str, int]]:
    """Turn a comma-separated host string into ``[(host, port), …]``."""
    if not hosts_csv:
        return []
    resolved_port = int(port) if port else 26379
    return [
        (host.strip(), resolved_port)
        for host in hosts_csv.split(",")
        if host.strip()
    ]


def build_sentinel_url(
    base_url: str,
    hosts_csv: str,
    port: str | int,
) -> str:
    """Construct a ``redis+sentinel://`` connection string.

    ``base_url`` supplies credentials, db index, and master service name.
    ``hosts_csv`` is a comma-separated list of sentinel hostnames.
    """
    cfg = parse_redis_url(base_url)
    auth = ""
    if cfg["username"] or cfg["password"]:
        auth = f"{cfg['username'] or ''}:{cfg['password'] or ''}@"
    nodes = ",".join(
        f"{host.strip()}:{port}" for host in hosts_csv.split(",") if host.strip()
    )
    return f"redis+sentinel://{auth}{nodes}/{cfg['db']}/{cfg['service']}"


def get_redis_client(async_mode: bool = False) -> Any | None:
    """Create a Redis connection using settings from environment variables.

    Returns ``None`` when Redis is not configured or the connection fails.
    """
    sentinel_list = get_sentinels_from_env(REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT)
    if not REDIS_URL and not sentinel_list:
        return None
    try:
        return get_redis_connection(
            REDIS_URL,
            redis_sentinels=sentinel_list,
            redis_cluster=REDIS_CLUSTER,
            async_mode=async_mode,
        )
    except Exception:
        log.debug("Could not establish Redis connection", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Sentinel proxy with automatic failover retry
# ---------------------------------------------------------------------------


class SentinelRedisProxy:
    """Transparent proxy that re-resolves the Sentinel master on connection errors.

    Every call (sync or async) is wrapped with retry logic so that transient
    Sentinel failovers are handled without caller intervention.
    """

    def __init__(
        self,
        sentinel: Any,
        service_name: str,
        *,
        async_mode: bool = True,
    ) -> None:
        self._sentinel = sentinel
        self._service_name = service_name
        self._async_mode = async_mode

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access with automatic Sentinel failover retry."""
        current_master = self._sentinel.master_for(self._service_name)
        original = getattr(current_master, name)

        # Non-callable or factory attributes pass through without wrapping.
        if not callable(original) or name in _FACTORY_METHODS:
            return original

        # Select the retry wrapper matching the execution mode.
        if not self._async_mode:
            return self._wrap_sync(name)
        return self._wrap_async(name, original)

    def _resolve_master(self) -> Any:
        """Ask Sentinel for the current master connection."""
        return self._sentinel.master_for(self._service_name)

    def _should_retry(self, attempt: int) -> bool:
        return attempt < REDIS_SENTINEL_MAX_RETRY_COUNT - 1

    def _log_retry(self, exc: Exception, attempt: int) -> None:
        log.debug(
            "Sentinel failover (%s) — retry %d/%d",
            type(exc).__name__,
            attempt + 1,
            REDIS_SENTINEL_MAX_RETRY_COUNT,
        )

    def _log_exhausted(self, exc: Exception) -> None:
        log.error(
            "Redis operation failed after %d retries: %s",
            REDIS_SENTINEL_MAX_RETRY_COUNT,
            exc,
        )

    # -- async wrappers -----------------------------------------------------

    def _wrap_async(self, name: str, attr: Any) -> Any:
        if inspect.isasyncgenfunction(attr):
            return self._wrap_async_gen(name)
        return self._wrap_async_call(name)

    def _wrap_async_gen(self, name: str) -> Any:
        proxy = self

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            async def _inner():
                for attempt in range(REDIS_SENTINEL_MAX_RETRY_COUNT):
                    try:
                        method = getattr(proxy._resolve_master(), name)
                        async for value in method(*args, **kwargs):
                            yield value
                        return
                    except _SENTINEL_RETRYABLE as exc:
                        if proxy._should_retry(attempt):
                            proxy._log_retry(exc, attempt)
                            if REDIS_RECONNECT_DELAY:
                                time.sleep(REDIS_RECONNECT_DELAY / 1000)
                            continue
                        proxy._log_exhausted(exc)
                        raise

            return _inner()

        return wrapper

    def _wrap_async_call(self, name: str) -> Any:
        proxy = self

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(REDIS_SENTINEL_MAX_RETRY_COUNT):
                try:
                    method = getattr(proxy._resolve_master(), name)
                    result = method(*args, **kwargs)
                    if inspect.iscoroutine(result):
                        return await result
                    return result
                except _SENTINEL_RETRYABLE as exc:
                    if proxy._should_retry(attempt):
                        proxy._log_retry(exc, attempt)
                        if REDIS_RECONNECT_DELAY:
                            await asyncio.sleep(REDIS_RECONNECT_DELAY / 1000)
                        continue
                    proxy._log_exhausted(exc)
                    raise

        return wrapper

    # -- sync wrapper -------------------------------------------------------

    def _wrap_sync(self, name: str) -> Any:
        proxy = self

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(REDIS_SENTINEL_MAX_RETRY_COUNT):
                try:
                    method = getattr(proxy._resolve_master(), name)
                    return method(*args, **kwargs)
                except _SENTINEL_RETRYABLE as exc:
                    if proxy._should_retry(attempt):
                        proxy._log_retry(exc, attempt)
                        if REDIS_RECONNECT_DELAY:
                            time.sleep(REDIS_RECONNECT_DELAY / 1000)
                        continue
                    proxy._log_exhausted(exc)
                    raise

        return wrapper


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------


def _socket_options() -> dict[str, Any]:
    """Collect optional socket-level kwargs once instead of repeating them."""
    opts: dict[str, Any] = {}
    if REDIS_SOCKET_CONNECT_TIMEOUT is not None:
        opts["socket_connect_timeout"] = REDIS_SOCKET_CONNECT_TIMEOUT
    if REDIS_SOCKET_KEEPALIVE:
        opts["socket_keepalive"] = True
    if REDIS_HEALTH_CHECK_INTERVAL:
        opts["health_check_interval"] = REDIS_HEALTH_CHECK_INTERVAL
    return opts


def _build_sentinel(
    redis_module: Any,
    url: str,
    sentinels: list[tuple[str, int]],
    decode_responses: bool,
    async_mode: bool,
) -> SentinelRedisProxy:
    """Create a SentinelRedisProxy from a redis URL and sentinel list."""
    cfg = parse_redis_url(url)
    sentinel = redis_module.sentinel.Sentinel(
        sentinels,
        port=cfg["port"],
        db=cfg["db"],
        username=cfg["username"],
        password=cfg["password"],
        decode_responses=decode_responses,
        socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
        **{k: v for k, v in _socket_options().items() if k != "socket_connect_timeout"},
    )
    return SentinelRedisProxy(sentinel, cfg["service"], async_mode=async_mode)


def get_redis_connection(
    redis_url: str | None,
    redis_sentinels: list[tuple[str, int]] | None = None,
    redis_cluster: bool = False,
    async_mode: bool = False,
    decode_responses: bool = True,
) -> Any | None:
    """Return a cached Redis connection (or create one).

    Supports three topologies in order of precedence:
    1. **Sentinel** — when ``redis_sentinels`` is non-empty.
    2. **Cluster** — when ``redis_cluster`` is True.
    3. **Standalone** — plain ``redis://`` connection.
    """
    cache_key = (
        redis_url,
        tuple(redis_sentinels) if redis_sentinels else (),
        async_mode,
        decode_responses,
    )
    if cache_key in _CONNECTION_POOL:
        return _CONNECTION_POOL[cache_key]

    extra = _socket_options()
    connection: Any = None

    # Pick the right redis module for sync vs async.
    if async_mode:
        import redis.asyncio as redis_mod
    else:
        import redis as redis_mod  # type: ignore[no-redef]

    if redis_sentinels:
        connection = _build_sentinel(redis_mod, redis_url, redis_sentinels, decode_responses, async_mode)
    elif redis_cluster:
        if not redis_url:
            raise ValueError("Redis URL is required for cluster mode.")
        connection = redis_mod.cluster.RedisCluster.from_url(
            redis_url, decode_responses=decode_responses, **extra,
        )
    elif redis_url:
        factory = getattr(redis_mod, "from_url", None) or redis_mod.Redis.from_url
        connection = factory(redis_url, decode_responses=decode_responses, **extra)

    _CONNECTION_POOL[cache_key] = connection
    return connection
