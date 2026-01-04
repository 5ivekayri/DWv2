"""Weather service that bridges multiple providers with caching."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable, List

import logging
import os

from django.core.cache.backends.base import BaseCache

from backend.core.abstractions import WeatherPoint, WeatherProvider, WeatherService


logger = logging.getLogger(__name__)


class WeatherServiceError(RuntimeError):
    """Raised when no provider can return weather data."""


class WeatherServiceBridge(WeatherService):
    """Combine multiple weather providers with fallback logic and caching."""

    cache_key_template = "weather:{lat:.4f}:{lon:.4f}"

    def __init__(
        self,
        providers: Iterable[WeatherProvider],
        cache: BaseCache,
        ttl: int,
    ) -> None:
        self._providers: List[WeatherProvider] = list(providers)
        self._cache = cache
        self._ttl = ttl
        self._testing_mode = os.environ.get("TESTING_MODE", "0") == "1"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:
        cache_key = self.cache_key_template.format(lat=latitude, lon=longitude)
        cached = self._cache.get(cache_key)
        if cached:
            return self._deserialize(cached)

        errors: List[Exception] = []
        for provider in self._providers:
            try:
                point = provider.get_weather(latitude, longitude)
            except Exception as exc:  # noqa: BLE001 - provider failures should be logged
                logger.warning("Weather provider %s failed: %s", provider.name, exc)
                errors.append(exc)
                continue

            self._cache.set(cache_key, self._serialize(point), self._ttl)
            if self._testing_mode:
                logger.info("Provider %s returned weather data", point.source)
            return point

        raise WeatherServiceError("All weather providers failed") from (errors[0] if errors else None)

    def _serialize(self, point: WeatherPoint) -> dict:
        payload = asdict(point)
        observed_at: datetime = payload["observed_at"]
        payload["observed_at"] = observed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return payload

    def _deserialize(self, payload: dict) -> WeatherPoint:
        observed_at = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
        return WeatherPoint(
            latitude=payload["latitude"],
            longitude=payload["longitude"],
            temperature_c=payload["temperature_c"],
            pressure_hpa=payload["pressure_hpa"],
            wind_speed_ms=payload["wind_speed_ms"],
            precipitation_mm=payload["precipitation_mm"],
            source=payload["source"],
            observed_at=observed_at,
        )
