"""Open-Meteo provider stub."""
from __future__ import annotations

from backend.core.abstractions import WeatherPoint, WeatherProvider


class OpenMeteoProvider(WeatherProvider):
    """Stub implementation for Open-Meteo."""

    name = "openmeteo"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:  # noqa: D401
        """Return weather observations from Open-Meteo."""
        raise NotImplementedError("TODO: integrate with Open-Meteo API")
