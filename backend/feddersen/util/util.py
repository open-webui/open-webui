from typing import Any
from datetime import datetime


class Cache:
    """Simple Cache for the User-Groups. After the cache_duration, the cache is invalidated.

    Args:
        cache_duration (int, optional): Duration in seconds for the cache. Defaults to 3600.
    """

    def __init__(self, cache_duration: int = 3600):
        self._cache: dict[str, tuple[Any, datetime]] = {}

        assert cache_duration > 0

        self.cache_duration = cache_duration

    def __getitem__(self, key: str) -> Any | None:
        value = self._cache.get(key)
        if value is not None:
            groups, created_at = value
            if (datetime.now() - created_at).total_seconds() < self.cache_duration:
                return groups
            del self._cache[key]

        return None

    def __setitem__(self, key: str, value: Any) -> None:
        self._cache[key] = (value, datetime.now())
