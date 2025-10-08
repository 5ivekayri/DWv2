from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Optional

from ..cache import WeatherCache
from ..entities import WeatherPoint
from ..providers.base import ProviderError, QuotaExceeded


class WeatherService:
    CURRENT_TTL = 10 * 60
    FORECAST_TTL = 30 * 60

    def __init__(
        self,
        *,
        local_station: Optional[Any],
        primary_provider: Any,
        fallback_provider: Any,
        cache: Optional[WeatherCache] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.local_station = local_station
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.cache = cache or WeatherCache()
        self._log = logger or logging.getLogger(self.__class__.__name__)

    # Public API ---------------------------------------------------------
    def get_current(self, latitude: float, longitude: float) -> WeatherPoint:
        local = self._try_local("current", latitude, longitude)
        if local is not None:
            return local
        cache_key = self._cache_key("current", latitude, longitude)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._fetch_with_fallback("current", latitude, longitude)
        self.cache.set(cache_key, result, self.CURRENT_TTL)
        return result

    def get_hourly(self, latitude: float, longitude: float, hours: int = 24) -> Iterable[WeatherPoint]:
        local = self._try_local("hourly", latitude, longitude, hours=hours)
        if local is not None:
            return local
        cache_key = self._cache_key("hourly", latitude, longitude, hours)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._fetch_with_fallback("hourly", latitude, longitude, hours=hours)
        self.cache.set(cache_key, result, self.FORECAST_TTL)
        return result

    def get_daily(self, latitude: float, longitude: float, days: int = 7) -> Iterable[WeatherPoint]:
        local = self._try_local("daily", latitude, longitude, days=days)
        if local is not None:
            return local
        cache_key = self._cache_key("daily", latitude, longitude, days)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._fetch_with_fallback("daily", latitude, longitude, days=days)
        self.cache.set(cache_key, result, self.FORECAST_TTL)
        return result

    # Helpers ------------------------------------------------------------
    def _try_local(self, method_name: str, *args, **kwargs):
        if not self.local_station:
            return None
        is_fresh = getattr(self.local_station, "is_fresh", None)
        if callable(is_fresh) and not is_fresh(method_name):
            return None
        method = getattr(self.local_station, method_name, None)
        if not callable(method):
            return None
        try:
            return method(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - safety
            self._log.error("Local station error", exc_info=exc)
            return None

    def _fetch_with_fallback(self, method_name: str, *args, **kwargs):
        for provider in (self.primary, self.fallback):
            method = getattr(provider, method_name, None)
            if not callable(method):
                continue
            try:
                return method(*args, **kwargs)
            except QuotaExceeded as exc:
                self._log.warning("Provider %s quota exceeded", provider.__class__.__name__)
                continue
            except ProviderError as exc:
                self._log.error("Provider %s failed: %s", provider.__class__.__name__, exc)
                continue
        raise ProviderError("all providers failed")

    def _cache_key(self, kind: str, latitude: float, longitude: float, extra: Optional[int] = None) -> str:
        if extra is not None:
            return f"weather:{kind}:{latitude:.3f}:{longitude:.3f}:{extra}"
        return f"weather:{kind}:{latitude:.3f}:{longitude:.3f}"


__all__ = ["WeatherService"]
