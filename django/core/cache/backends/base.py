"""Cache base classes for the Django stub."""
from __future__ import annotations

import time
from typing import Any


class BaseCache:
    """Simplified cache backend."""

    def __init__(self, alias: str = "default") -> None:
        self.alias = alias

    def get(self, key: str, default: Any | None = None) -> Any:
        raise NotImplementedError

    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class LocMemCache(BaseCache):
    """In-memory cache with optional TTL support."""

    def __init__(self, alias: str = "default") -> None:
        super().__init__(alias)
        self._store: dict[str, tuple[Any, float | None]] = {}

    def get(self, key: str, default: Any | None = None) -> Any:
        item = self._store.get(key)
        if not item:
            return default
        value, expires_at = item
        if expires_at is not None and expires_at <= time.time():
            self._store.pop(key, None)
            return default
        return value

    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        expires_at = time.time() + timeout if timeout else None
        self._store[key] = (value, expires_at)

    def clear(self) -> None:
        self._store.clear()
