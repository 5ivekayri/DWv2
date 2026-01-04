"""Open-Meteo weather provider."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from typing import Optional

import requests

from backend.core.abstractions import WeatherPoint, WeatherProvider


logger = logging.getLogger(__name__)


class OpenMeteoProvider(WeatherProvider):
    """Integration with the Open-Meteo current weather endpoint."""

    name = "openmeteo"

    def __init__(
        self,
        *,
        base_url: str = "https://api.open-meteo.com/v1/forecast",
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url
        self.session = session or requests.Session()
        self._testing_mode = os.environ.get("TESTING_MODE", "0") == "1"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:  # noqa: D401
        """Return weather observations from Open-Meteo."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,pressure_msl,wind_speed_10m,precipitation",
        }
        response = self.session.get(self.base_url, params=params, timeout=10)
        self._log_response(response.url, params, response)
        response.raise_for_status()

        data = response.json()
        current = data.get("current") or data.get("current_weather")
        if not current:
            raise RuntimeError("missing current weather")

        observed_at = self._parse_time(current.get("time"))
        return WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            temperature_c=float(current.get("temperature_2m") or current.get("temperature")),
            pressure_hpa=float(current.get("pressure_msl")),
            wind_speed_ms=float(current.get("wind_speed_10m") or current.get("windspeed")),
            precipitation_mm=float(current.get("precipitation", 0.0)),
            source=self.name,
            observed_at=observed_at,
        )

    def _parse_time(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(tz=timezone.utc)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _log_response(self, url: str, params: dict, response: requests.Response) -> None:
        if not self._testing_mode:
            return
        body_preview = response.text[:500]
        logger.info(
            "Open-Meteo request", extra={"url": url, "params": params, "status": response.status_code, "body": body_preview}
        )
