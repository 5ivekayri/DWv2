from __future__ import annotations

import time
from typing import Any, Dict, Tuple


class WeatherCache:
    """A lightweight TTL cache emulating Redis behaviour for tests."""

    def __init__(self, time_func=time.monotonic) -> None:
        self._time_func = time_func
        self._storage: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        item = self._storage.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < self._time_func():
            self._storage.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._storage[key] = (self._time_func() + ttl, value)

    def clear(self) -> None:
        self._storage.clear()


__all__ = ["WeatherCache"]
