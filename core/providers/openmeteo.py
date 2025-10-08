from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from .base import ProviderError, WeatherProvider
from ..entities import WeatherPoint


def _kmh_to_ms(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value / 3.6, 2)


class OpenMeteoProvider(WeatherProvider):
    base_url = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, base_url: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.base_url = base_url or self.base_url
        self._log = logging.getLogger(self.__class__.__name__)

    def current(self, latitude: float, longitude: float) -> WeatherPoint:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "pressure_msl", "windspeed_10m", "precipitation"],
            "timezone": "UTC",
        }
        response = self._request("GET", self.base_url, params=params)
        data = self._json(response)
        current = data.get("current") or data.get("current_weather")
        if not current:
            raise ProviderError("missing current weather")
        timestamp = self._parse_time(current.get("time"))
        return WeatherPoint(
            timestamp=timestamp,
            temperature_c=_safe_float(current.get("temperature_2m")) or _safe_float(current.get("temperature")),
            pressure_hpa=_safe_float(current.get("pressure_msl")),
            wind_speed_ms=_kmh_to_ms(_safe_float(current.get("windspeed_10m")) or _safe_float(current.get("windspeed"))),
            precipitation_mm=_safe_float(current.get("precipitation")),
            source="open-meteo:current",
        )

    def hourly(self, latitude: float, longitude: float, hours: int = 24) -> List[WeatherPoint]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ["temperature_2m", "pressure_msl", "windspeed_10m", "precipitation"],
            "timezone": "UTC",
        }
        response = self._request("GET", self.base_url, params=params)
        data = self._json(response)
        hourly = data.get("hourly") or {}
        timestamps = hourly.get("time") or []
        temps = hourly.get("temperature_2m") or []
        pressures = hourly.get("pressure_msl") or []
        winds = hourly.get("windspeed_10m") or []
        precipitation = hourly.get("precipitation") or []
        if not timestamps:
            raise ProviderError("missing hourly data")
        result: List[WeatherPoint] = []
        for idx, ts in enumerate(timestamps[:hours]):
            result.append(
                WeatherPoint(
                    timestamp=self._parse_time(ts),
                    temperature_c=_safe_index(temps, idx),
                    pressure_hpa=_safe_index(pressures, idx),
                    wind_speed_ms=_kmh_to_ms(_safe_index(winds, idx)),
                    precipitation_mm=_safe_index(precipitation, idx),
                    source="open-meteo:hour",
                )
            )
        return result

    def daily(self, latitude: float, longitude: float, days: int = 7) -> List[WeatherPoint]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "windspeed_10m_max"],
            "timezone": "UTC",
        }
        response = self._request("GET", self.base_url, params=params)
        data = self._json(response)
        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            raise ProviderError("missing daily data")
        temps_max = daily.get("temperature_2m_max") or []
        temps_min = daily.get("temperature_2m_min") or []
        precipitation = daily.get("precipitation_sum") or []
        winds = daily.get("windspeed_10m_max") or []
        result: List[WeatherPoint] = []
        for idx, date_str in enumerate(dates[:days]):
            avg_temp = _average([_safe_index(temps_min, idx), _safe_index(temps_max, idx)])
            result.append(
                WeatherPoint(
                    timestamp=self._parse_time(date_str),
                    temperature_c=avg_temp,
                    pressure_hpa=None,
                    wind_speed_ms=_kmh_to_ms(_safe_index(winds, idx)),
                    precipitation_mm=_safe_index(precipitation, idx),
                    source="open-meteo:day",
                )
            )
        return result

    # helpers ------------------------------------------------------------
    def _json(self, response) -> dict:
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - invalid json
            self._log.error("Failed to decode JSON", exc_info=exc)
            raise ProviderError("invalid json") from exc

    def _parse_time(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.utcnow()
        if value.endswith("Z"):
            value = value[:-1]
        return datetime.fromisoformat(value)


def _safe_float(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


def _safe_index(values: List[Optional[float]], index: int) -> Optional[float]:
    try:
        value = values[index]
    except (IndexError, TypeError):  # pragma: no cover - defensive
        return None
    return _safe_float(value)


def _average(values: List[Optional[float]]) -> Optional[float]:
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


__all__ = ["OpenMeteoProvider"]
