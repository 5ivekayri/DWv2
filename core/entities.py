from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WeatherPoint:
    """Normalized weather point representation.

    Values are stored in SI-like units to make providers interchangeable:
    - temperature in Celsius
    - pressure in hectopascal (hPa)
    - wind speed in metres per second (m/s)
    - precipitation in millimetres (mm)
    """

    timestamp: datetime
    temperature_c: Optional[float]
    pressure_hpa: Optional[float]
    wind_speed_ms: Optional[float]
    precipitation_mm: Optional[float]
    source: str


__all__ = ["WeatherPoint"]
