"""Cache access helpers for the Django stub."""
from __future__ import annotations

from typing import Any, Dict

from django.core.cache.backends.base import BaseCache, LocMemCache


class CacheHandler:
    def __init__(self) -> None:
        self._config: Dict[str, Dict[str, Any]] = {"default": {"BACKEND": "locmem"}}
        self._caches: Dict[str, BaseCache] = {}

    def configure(self, config: Dict[str, Dict[str, Any]] | None) -> None:
        if config:
            self._config = config
        self._caches.clear()

    def __getitem__(self, alias: str) -> BaseCache:
        if alias not in self._caches:
            self._caches[alias] = LocMemCache(alias)
        return self._caches[alias]

    def clear(self) -> None:
        for cache in self._caches.values():
            cache.clear()


caches = CacheHandler()


class _CacheProxy:
    def __getattr__(self, item: str) -> Any:
        return getattr(caches["default"], item)


cache = _CacheProxy()
