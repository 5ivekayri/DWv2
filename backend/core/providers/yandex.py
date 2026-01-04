"""Yandex weather provider stub."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.core.abstractions import WeatherPoint, WeatherProvider


class YandexWeatherProvider(WeatherProvider):
    """Stub for the Yandex Weather API integration."""

    name = "yandex"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:  # noqa: D401
        """Return weather observations from Yandex Weather."""
        # Minimal deterministic payload for local development. Replace with
        # real API call once the integration is available.
        return WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            temperature_c=18.5,
            pressure_hpa=1010.0,
            wind_speed_ms=4.2,
            precipitation_mm=0.3,
            observed_at=datetime.now(tz=timezone.utc),
        )
