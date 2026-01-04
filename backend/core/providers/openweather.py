"""OpenWeather weather provider."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from typing import Optional

import requests

from backend.core.abstractions import WeatherPoint, WeatherProvider


logger = logging.getLogger(__name__)


class OpenWeatherProvider(WeatherProvider):
    """Integration with the OpenWeather current weather endpoint."""

    name = "openweather"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openweathermap.org/data/2.5/weather",
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.session = session or requests.Session()
        self._testing_mode = os.environ.get("TESTING_MODE", "0") == "1"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:  # noqa: D401
        """Return weather observations from OpenWeather."""
        params = {"lat": latitude, "lon": longitude, "appid": self.api_key, "units": "metric"}
        response = self.session.get(self.base_url, params=params, timeout=10)
        self._log_response(response.url, params, response)
        response.raise_for_status()

        data = response.json()
        main = data.get("main") or {}
        wind = data.get("wind") or {}
        rain = data.get("rain") or {}

        observed_at = self._parse_timestamp(data.get("dt"))
        temperature = main.get("temp")
        pressure = main.get("pressure")
        wind_speed = wind.get("speed")
        precipitation = rain.get("1h") or rain.get("3h") or 0.0

        return WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            temperature_c=float(temperature),
            pressure_hpa=float(pressure),
            wind_speed_ms=float(wind_speed),
            precipitation_mm=float(precipitation),
            source=self.name,
            observed_at=observed_at,
        )

    def _parse_timestamp(self, value: int | None) -> datetime:
        if value is None:
            return datetime.now(tz=timezone.utc)
        return datetime.fromtimestamp(int(value), tz=timezone.utc)

    def _log_response(self, url: str, params: dict, response: requests.Response) -> None:
        if not self._testing_mode:
            return
        body_preview = response.text[:500]
        logger.info(
            "OpenWeather request", extra={"url": url, "params": params, "status": response.status_code, "body": body_preview}
        )
