"""Open-Meteo provider stub."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.core.abstractions import WeatherPoint, WeatherProvider


class OpenMeteoProvider(WeatherProvider):
    """Stub implementation for Open-Meteo."""

    name = "openmeteo"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:  # noqa: D401
        """Return weather observations from Open-Meteo."""
        return WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            temperature_c=17.0,
            pressure_hpa=1008.0,
            wind_speed_ms=5.0,
            precipitation_mm=0.1,
            observed_at=datetime.now(tz=timezone.utc),
        )
