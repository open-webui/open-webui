"""Dual-mode voice session ownership registry.

Tracks which worker/socket owns each active voice session. Uses in-memory
dicts for single-worker mode and RedisDict/RedisLock for multi-worker mode.
Reuses OWUI's existing Redis infrastructure — no custom Lua scripts.
"""

import asyncio
import logging
import time
from typing import Optional

from pydantic import BaseModel

from open_webui.env import (
    INSTANCE_ID,
    REDIS_KEY_PREFIX,
    WEBSOCKET_MANAGER,
    WEBSOCKET_REDIS_CLUSTER,
    WEBSOCKET_REDIS_LOCK_TIMEOUT,
    WEBSOCKET_REDIS_URL,
    WEBSOCKET_SENTINEL_HOSTS,
    WEBSOCKET_SENTINEL_PORT,
)
from open_webui.utils.redis import get_sentinels_from_env

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ownership record
# ---------------------------------------------------------------------------

class OwnershipRecord(BaseModel):
    voice_session_id: str
    user_id: str
    sid: str
    call_id: str = ""
    model_id: str = ""
    chat_id: str = ""
    generation: int = 1
    worker_instance_id: str = ""
    state: str = "active"  # active | ending | ended
    created_at: float = 0.0
    updated_at: float = 0.0


# ---------------------------------------------------------------------------
# Dual-mode registry storage
# ---------------------------------------------------------------------------

_redis_sentinels = get_sentinels_from_env(WEBSOCKET_SENTINEL_HOSTS, WEBSOCKET_SENTINEL_PORT)

if WEBSOCKET_MANAGER == "redis":
    from open_webui.socket.utils import RedisDict, RedisLock

    log.info("Ownership registry: Redis mode")

    _registry = RedisDict(
        f"{REDIS_KEY_PREFIX}:rt_ownership",
        redis_url=WEBSOCKET_REDIS_URL,
        redis_sentinels=_redis_sentinels,
        redis_cluster=WEBSOCKET_REDIS_CLUSTER,
    )
else:
    log.info("Ownership registry: in-memory mode")
    _registry: dict = {}


# ---------------------------------------------------------------------------
# Per-session locks (dual-mode)
# ---------------------------------------------------------------------------

_memory_locks: dict[str, asyncio.Lock] = {}


def _get_lock(voice_session_id: str):
    """Get a per-session lock. Returns RedisLock in Redis mode, asyncio.Lock in memory mode."""
    if WEBSOCKET_MANAGER == "redis":
        return RedisLock(
            redis_url=WEBSOCKET_REDIS_URL,
            lock_name=f"{REDIS_KEY_PREFIX}:rt_ownership_lock:{voice_session_id}",
            timeout_secs=WEBSOCKET_REDIS_LOCK_TIMEOUT,
            redis_sentinels=_redis_sentinels,
            redis_cluster=WEBSOCKET_REDIS_CLUSTER,
        )
    else:
        if voice_session_id not in _memory_locks:
            _memory_locks[voice_session_id] = asyncio.Lock()
        return _memory_locks[voice_session_id]


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

async def claim_start(
    voice_session_id: str,
    user_id: str,
    sid: str,
    call_id: str = "",
    model_id: str = "",
    chat_id: str = "",
) -> Optional[OwnershipRecord]:
    """Claim ownership of a voice session. Returns the record with handoff token, or None if already owned by another."""
    now = time.time()
    lock = _get_lock(voice_session_id)

    if WEBSOCKET_MANAGER == "redis":
        if not lock.aquire_lock():
            log.warning(
                "claim_start: could not acquire lock for voice_session_id=%s",
                voice_session_id,
            )
            return None
        try:
            existing = _registry.get(voice_session_id)
            if existing and existing.get("state") == "active" and existing.get("sid") != sid:
                log.warning(
                    "claim_start: session %s already owned by sid=%s (requested by sid=%s)",
                    voice_session_id, existing.get("sid"), sid,
                )
                return None

            generation = (existing.get("generation", 0) + 1) if existing else 1
            record = OwnershipRecord(
                voice_session_id=voice_session_id,
                user_id=user_id,
                sid=sid,
                call_id=call_id,
                model_id=model_id,
                chat_id=chat_id,
                generation=generation,
                worker_instance_id=INSTANCE_ID,
                state="active",
                created_at=now,
                updated_at=now,
            )
            _registry[voice_session_id] = record.model_dump()
            return record
        finally:
            lock.release_lock()
    else:
        async with lock:
            existing = _registry.get(voice_session_id)
            if existing and existing.get("state") == "active" and existing.get("sid") != sid:
                log.warning(
                    "claim_start: session %s already owned by sid=%s (requested by sid=%s)",
                    voice_session_id, existing.get("sid"), sid,
                )
                return None

            generation = (existing.get("generation", 0) + 1) if existing else 1
            record = OwnershipRecord(
                voice_session_id=voice_session_id,
                user_id=user_id,
                sid=sid,
                call_id=call_id,
                model_id=model_id,
                chat_id=chat_id,
                generation=generation,
                worker_instance_id=INSTANCE_ID,
                state="active",
                created_at=now,
                updated_at=now,
            )
            _registry[voice_session_id] = record.model_dump()
            return record


async def release(voice_session_id: str) -> bool:
    """Release ownership of a voice session. Returns True if released, False if not found."""
    lock = _get_lock(voice_session_id)

    if WEBSOCKET_MANAGER == "redis":
        if not lock.aquire_lock():
            log.warning("release: could not acquire lock for %s", voice_session_id)
            return False
        try:
            existing = _registry.get(voice_session_id)
            if not existing:
                return False
            existing["state"] = "ended"
            existing["updated_at"] = time.time()
            _registry[voice_session_id] = existing
            return True
        finally:
            lock.release_lock()
    else:
        async with lock:
            existing = _registry.get(voice_session_id)
            if not existing:
                return False
            existing["state"] = "ended"
            existing["updated_at"] = time.time()
            _registry[voice_session_id] = existing
            return True


async def get_record(voice_session_id: str) -> Optional[OwnershipRecord]:
    """Look up the ownership record for a voice session."""
    data = _registry.get(voice_session_id)
    if not data:
        return None
    try:
        return OwnershipRecord(**data)
    except Exception:
        log.warning("get_record: invalid record for %s", voice_session_id)
        return None


def get_records_by_sid(sid: str) -> list[OwnershipRecord]:
    """Get all ownership records for a given socket ID. Used in disconnect cleanup."""
    results = []
    try:
        for _key, data in list(_registry.items()):
            if data and data.get("sid") == sid and data.get("state") == "active":
                try:
                    results.append(OwnershipRecord(**data))
                except Exception:
                    pass
    except Exception as exc:
        log.warning("get_records_by_sid failed: %s", exc)
    return results


def get_record_by_chat(chat_id: str) -> Optional[OwnershipRecord]:
    """Get the active ownership record for a chat. Used for conflict detection."""
    try:
        for _key, data in list(_registry.items()):
            if data and data.get("chat_id") == chat_id and data.get("state") == "active":
                try:
                    return OwnershipRecord(**data)
                except Exception:
                    pass
    except Exception as exc:
        log.warning("get_record_by_chat failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_ended_records(max_age_seconds: float = 300.0) -> int:
    """Remove ended records older than max_age_seconds. Returns count removed."""
    cutoff = time.time() - max_age_seconds
    removed = 0
    try:
        for key in list(_registry.keys()):
            data = _registry.get(key)
            if (
                data
                and data.get("state") == "ended"
                and data.get("updated_at", 0) < cutoff
            ):
                try:
                    del _registry[key]
                    removed += 1
                except KeyError:
                    pass
    except Exception as exc:
        log.warning("cleanup_ended_records failed: %s", exc)

    # Clean up memory locks for ended sessions
    if WEBSOCKET_MANAGER != "redis":
        for key in list(_memory_locks.keys()):
            if key not in _registry:
                _memory_locks.pop(key, None)

    return removed
