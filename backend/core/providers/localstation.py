"""Fallback provider using a local weather station placeholder."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.core.abstractions import WeatherPoint, WeatherProvider


class LocalStationProvider(WeatherProvider):
    """Placeholder provider until the local station integration is available."""

    name = "localstation"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:
        """Return synthetic data for development and testing purposes."""
        # TODO: replace with actual local station integration once available.
        return WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            temperature_c=20.0,
            pressure_hpa=1013.0,
            wind_speed_ms=3.5,
            precipitation_mm=0.0,
            observed_at=datetime.now(tz=timezone.utc),
        )
