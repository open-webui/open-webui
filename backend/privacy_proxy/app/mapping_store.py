import time
import threading
import os
import json

try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL")
    _redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None
    if _redis_client:
        _redis_client.ping()
        print("[MAPPING STORE] Redis connected")
except Exception as e:
    print(f"[MAPPING STORE] Redis unavailable, using memory only: {e}")
    _redis_client = None


class MappingStore:
    def __init__(self, ttl: int = 3600):
        self._store = {}
        self._timestamps = {}
        self._ttl = ttl
        self._lock = threading.Lock()

    def get_mapping(self, session_id: str) -> dict:
        with self._lock:
            self._cleanup(session_id)
            return self._store.setdefault(session_id, {})

    def get_store(self) -> dict:
        return _RedisAwareStore(self._store, self._ttl)

    def _cleanup(self, session_id: str):
        now = time.time()
        if session_id in self._timestamps:
            if now - self._timestamps[session_id] > self._ttl:
                del self._store[session_id]
                del self._timestamps[session_id]
        self._timestamps[session_id] = now


class _RedisAwareStore:
    def __init__(self, memory: dict, ttl: int):
        self._memory = memory
        self._ttl = ttl

    def get(self, session_id: str, default=None):
        if session_id in self._memory:
            return self._memory[session_id]
        if _redis_client:
            try:
                raw = _redis_client.get(f"garnet:mapping:{session_id}")
                if raw:
                    mapping = json.loads(raw)
                    self._memory[session_id] = mapping
                    print(f"[MAPPING STORE] Restored from Redis: {session_id}")
                    return mapping
            except Exception as e:
                print(f"[MAPPING STORE] Redis read error: {e}")
        return default

    def setdefault(self, session_id: str, default=None):
        existing = self.get(session_id)
        if existing is not None:
            return _TrackedDict(session_id, existing, self)
        value = default if default is not None else {}
        self[session_id] = value
        return _TrackedDict(session_id, value, self)

    def __getitem__(self, session_id: str):
        result = self.get(session_id)
        if result is None:
            raise KeyError(session_id)
        return result

    def __setitem__(self, session_id: str, mapping: dict):
        self._memory[session_id] = mapping
        if _redis_client:
            try:
                _redis_client.setex(
                    f"garnet:mapping:{session_id}",
                    self._ttl,
                    json.dumps(mapping)
                )
            except Exception as e:
                print(f"[MAPPING STORE] Redis write error: {e}")

    def flush(self, session_id: str):
        if _redis_client and session_id in self._memory:
            try:
                _redis_client.setex(
                    f"garnet:mapping:{session_id}",
                    self._ttl,
                    json.dumps(self._memory[session_id])
                )
            except Exception as e:
                print(f"[MAPPING STORE] Redis flush error: {e}")

    def __contains__(self, session_id: str):
        return self.get(session_id) is not None


class _TrackedDict(dict):
    def __init__(self, session_id: str, data: dict, store: '_RedisAwareStore'):
        super().__init__(data)
        self._session_id = session_id
        self._store = store

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._store._memory[self._session_id] = dict(self)

    def flush(self):
        self._store.flush(self._session_id)