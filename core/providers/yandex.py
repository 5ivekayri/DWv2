from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from .base import ProviderError, WeatherProvider
from ..entities import WeatherPoint


def _mmhg_to_hpa(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value * 1.33322, 2)


class YandexWeatherProvider(WeatherProvider):
    base_url = "https://api.weather.yandex.ru/v2/forecast"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url or self.base_url
        self._log = logging.getLogger(self.__class__.__name__)

    # Public API ---------------------------------------------------------
    def current(self, latitude: float, longitude: float) -> WeatherPoint:
        data = self._fetch(latitude, longitude, hours=False, limit=1)
        fact = data.get("fact")
        if not fact:
            raise ProviderError("missing fact in response")
        timestamp = self._extract_timestamp(fact, data.get("now"))
        return self._build_point(fact, timestamp, source="yandex:fact")

    def hourly(self, latitude: float, longitude: float, hours: int = 24) -> List[WeatherPoint]:
        data = self._fetch(latitude, longitude, hours=True, limit=1)
        forecasts = data.get("forecasts") or []
        if not forecasts:
            raise ProviderError("missing forecasts in response")
        forecast = forecasts[0]
        base_date = forecast.get("date")
        hours_data = forecast.get("hours") or []
        if not base_date or not hours_data:
            raise ProviderError("missing hourly data")
        result: List[WeatherPoint] = []
        for hour in hours_data[:hours]:
            timestamp = self._build_hour_timestamp(base_date, hour.get("hour"))
            result.append(self._build_point(hour, timestamp, source="yandex:hour"))
        return result

    def daily(self, latitude: float, longitude: float, days: int = 7) -> List[WeatherPoint]:
        data = self._fetch(latitude, longitude, hours=False, limit=days)
        forecasts = data.get("forecasts") or []
        if not forecasts:
            raise ProviderError("missing forecasts in response")
        result: List[WeatherPoint] = []
        for forecast in forecasts[:days]:
            parts = forecast.get("parts") or {}
            day_part = parts.get("day") or parts.get("day_short") or parts.get("whole")
            if not day_part:
                raise ProviderError("missing day part in forecast")
            timestamp = datetime.fromisoformat(forecast["date"])
            result.append(self._build_point(day_part, timestamp, source="yandex:day"))
        return result

    # Helpers ------------------------------------------------------------
    def _fetch(self, latitude: float, longitude: float, *, hours: bool, limit: int) -> dict:
        params = {
            "lat": latitude,
            "lon": longitude,
            "lang": "en_US",
            "hours": str(hours).lower(),
            "limit": limit,
            "extra": "true",
        }
        headers = {"X-Yandex-API-Key": self.api_key}
        response = self._request("GET", self.base_url, params=params, headers=headers)
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - invalid json
            self._log.error("Failed to decode JSON", exc_info=exc)
            raise ProviderError("invalid json") from exc

    def _build_point(self, payload: dict, timestamp: datetime, *, source: str) -> WeatherPoint:
        return WeatherPoint(
            timestamp=timestamp,
            temperature_c=_safe_float(payload.get("temp")) or _safe_float(payload.get("temp_avg")),
            pressure_hpa=self._extract_pressure(payload),
            wind_speed_ms=_safe_float(payload.get("wind_speed")),
            precipitation_mm=self._extract_precipitation(payload),
            source=source,
        )

    def _extract_timestamp(self, payload: dict, fallback_now: Optional[int]) -> datetime:
        obs_time = payload.get("obs_time") or fallback_now
        if obs_time:
            return datetime.fromtimestamp(int(obs_time), tz=timezone.utc)
        return datetime.now(tz=timezone.utc)

    def _build_hour_timestamp(self, date_str: str, hour_str: Optional[str]) -> datetime:
        hour = int(hour_str or 0)
        date = datetime.fromisoformat(date_str)
        return date.replace(hour=hour, minute=0, second=0, microsecond=0)

    def _extract_pressure(self, payload: dict) -> Optional[float]:
        if "pressure_h_pa" in payload:  # Yandex occasionally uses this typo
            value = _safe_float(payload.get("pressure_h_pa"))
            if value is not None:
                return value
        pressure_pa = _safe_float(payload.get("pressure_pa"))
        if pressure_pa is not None:
            return round(pressure_pa / 100, 2)
        pressure_mm = _safe_float(payload.get("pressure_mm"))
        return _mmhg_to_hpa(pressure_mm)

    def _extract_precipitation(self, payload: dict) -> Optional[float]:
        if "precipitation" in payload:
            return _safe_float(payload.get("precipitation"))
        if "prec_mm" in payload:
            return _safe_float(payload.get("prec_mm"))
        if "prec_mm_min" in payload and "prec_mm_max" in payload:
            values = [_safe_float(payload.get("prec_mm_min")), _safe_float(payload.get("prec_mm_max"))]
            values = [v for v in values if v is not None]
            if values:
                return sum(values) / len(values)
        return None


def _safe_float(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


__all__ = ["YandexWeatherProvider"]
