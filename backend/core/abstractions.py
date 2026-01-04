"""Core abstractions for the weather domain."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class WeatherPoint:
    """Normalized weather observation."""

    latitude: float
    longitude: float
    temperature_c: float
    pressure_hpa: float
    wind_speed_ms: float
    precipitation_mm: float
    source: str
    observed_at: datetime


class WeatherProvider(Protocol):
    """A data source capable of returning weather observations."""

    name: str

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:
        """Fetch a single observation for the provided coordinates."""
        ...


class WeatherService(Protocol):
    """High level service that exposes weather information to the API layer."""

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:
        """Return a normalized observation for the provided coordinates."""
        ...
