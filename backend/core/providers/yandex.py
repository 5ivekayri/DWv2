"""Yandex weather provider stub."""
from __future__ import annotations

from backend.core.abstractions import WeatherPoint, WeatherProvider


class YandexWeatherProvider(WeatherProvider):
    """Stub for the Yandex Weather API integration."""

    name = "yandex"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:  # noqa: D401
        """Return weather observations from Yandex Weather."""
        raise NotImplementedError("TODO: integrate with Yandex Weather API")
