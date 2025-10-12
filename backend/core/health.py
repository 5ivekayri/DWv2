"""In-memory health registry for the admin dashboard.

The project does not have access to the real database layer inside this kata
so the registry keeps everything in memory.  The goal is to provide a clean
surface for the API layer and to make the registry deterministic for tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class CacheStats:
    """Simple container for cache related counters."""

    hits: int = 0
    misses: int = 0
    keys: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "keys": self.keys}


class HealthRegistry:
    """Stores heartbeat, provider error counters and cache stats."""

    def __init__(self) -> None:
        self._station_last_seen: Dict[str, str] = {}
        self._provider_errors: Dict[str, int] = {}
        self._cache_stats: CacheStats = CacheStats()
        self._lock = Lock()

    # -- Station heartbeats -------------------------------------------------
    def record_station_heartbeat(
        self, station_id: str, when: Optional[datetime] = None
    ) -> None:
        if not station_id:
            raise ValueError("station_id must be provided")
        when = when or datetime.now(timezone.utc)
        iso_value = self._format_datetime(when)
        with self._lock:
            self._station_last_seen[station_id] = iso_value

    def bulk_station_update(self, updates: Mapping[str, datetime]) -> None:
        if not updates:
            return
        with self._lock:
            for station_id, when in updates.items():
                if not station_id:
                    raise ValueError("station_id must be provided")
                when = when or datetime.now(timezone.utc)
                self._station_last_seen[station_id] = self._format_datetime(when)

    # -- Provider errors ----------------------------------------------------
    def record_provider_error(self, provider: str, increment: int = 1) -> None:
        if not provider:
            raise ValueError("provider must be provided")
        if increment <= 0:
            raise ValueError("increment must be positive")
        with self._lock:
            self._provider_errors[provider] = (
                self._provider_errors.get(provider, 0) + increment
            )

    def extend_provider_errors(self, counters: Mapping[str, int]) -> None:
        if not counters:
            return
        with self._lock:
            for provider, value in counters.items():
                if not provider:
                    raise ValueError("provider must be provided")
                if value < 0:
                    raise ValueError("error counters must be non-negative")
                self._provider_errors[provider] = (
                    self._provider_errors.get(provider, 0) + value
                )

    def drain_provider_errors(self) -> Dict[str, int]:
        with self._lock:
            snapshot = dict(self._provider_errors)
            self._provider_errors.clear()
            return snapshot

    # -- Cache stats --------------------------------------------------------
    def set_cache_stats(self, stats: Optional[Mapping[str, int]]) -> None:
        if not stats:
            self._cache_stats = CacheStats()
            return
        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        keys = int(stats.get("keys", 0))
        self._cache_stats = CacheStats(hits=hits, misses=misses, keys=keys)

    # -- Snapshot -----------------------------------------------------------
    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            stations = dict(self._station_last_seen)
            providers = dict(self._provider_errors)
            cache = self._cache_stats.as_dict()
        return {"stations": stations, "providers": providers, "cache": cache}

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
