from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from core.cache import WeatherCache
from core.entities import WeatherPoint
from core.providers.base import ProviderError
from core.providers.openmeteo import OpenMeteoProvider
from core.providers.yandex import YandexWeatherProvider
from core.services.weather import WeatherService


class LocalStationStub:
    def __init__(self, points: dict[str, WeatherPoint], fresh: bool = True) -> None:
        self._points = points
        self._fresh = fresh

    def is_fresh(self, method: str) -> bool:
        return self._fresh

    def current(self, *args, **kwargs) -> WeatherPoint:
        return self._points["current"]

    def hourly(self, *args, **kwargs) -> List[WeatherPoint]:
        return self._points["hourly"]

    def daily(self, *args, **kwargs) -> List[WeatherPoint]:
        return self._points["daily"]


class TimeController:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def make_point(source: str, temp: float = 10.0) -> WeatherPoint:
    return WeatherPoint(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        temperature_c=temp,
        pressure_hpa=1000.0,
        wind_speed_ms=5.0,
        precipitation_mm=0.1,
        source=source,
    )


def test_yandex_current_normalization(requests_mock):
    provider = YandexWeatherProvider(api_key="test", base_url="https://yandex.test/forecast")
    requests_mock.get(
        "https://yandex.test/forecast",
        json={
            "now": 1690000000,
            "fact": {
                "temp": 12,
                "pressure_mm": 750,
                "wind_speed": 5,
                "precipitation": 0.4,
            },
        },
    )

    point = provider.current(55.7, 37.6)

    assert point.temperature_c == 12
    assert point.pressure_hpa == pytest.approx(999.92, rel=1e-3)
    assert point.wind_speed_ms == 5
    assert point.precipitation_mm == 0.4
    assert point.timestamp == datetime.fromtimestamp(1690000000, tz=timezone.utc)


def test_openmeteo_hourly_normalization(requests_mock):
    provider = OpenMeteoProvider(base_url="https://openmeteo.test")
    requests_mock.get(
        "https://openmeteo.test",
        json={
            "hourly": {
                "time": ["2023-10-10T00:00", "2023-10-10T01:00"],
                "temperature_2m": [5.0, 6.0],
                "pressure_msl": [1010.0, 1011.0],
                "windspeed_10m": [36.0, 18.0],
                "precipitation": [1.2, 0.0],
            }
        },
    )

    forecast = provider.hourly(55.7, 37.6)

    assert len(forecast) == 2
    assert forecast[0].wind_speed_ms == pytest.approx(10.0, rel=1e-3)
    assert forecast[1].wind_speed_ms == pytest.approx(5.0, rel=1e-3)
    assert forecast[0].pressure_hpa == 1010.0
    assert forecast[0].source == "open-meteo:hour"


def test_weather_service_prefers_local_station(requests_mock):
    local_point = make_point("local")
    station = LocalStationStub(
        {
            "current": local_point,
            "hourly": [local_point],
            "daily": [local_point],
        }
    )
    yandex = YandexWeatherProvider(api_key="test", base_url="https://yandex.test/forecast")
    openmeteo = OpenMeteoProvider(base_url="https://openmeteo.test")
    service = WeatherService(local_station=station, primary_provider=yandex, fallback_provider=openmeteo)

    point = service.get_current(1.0, 1.0)

    assert point.source == "local"


def test_weather_service_falls_back_on_quota(requests_mock):
    yandex = YandexWeatherProvider(api_key="test", base_url="https://yandex.test/forecast")
    openmeteo = OpenMeteoProvider(base_url="https://openmeteo.test")
    service = WeatherService(local_station=None, primary_provider=yandex, fallback_provider=openmeteo)

    requests_mock.get("https://yandex.test/forecast", status_code=429, text="quota exceeded")
    requests_mock.get(
        "https://openmeteo.test",
        json={
            "current": {
                "time": "2023-10-10T00:00",
                "temperature_2m": 3.0,
                "pressure_msl": 1005.0,
                "windspeed_10m": 18.0,
                "precipitation": 0.0,
            }
        },
    )

    point = service.get_current(1.0, 1.0)

    assert point.source == "open-meteo:current"
    assert requests_mock.call_count == 2


def test_weather_service_caches_current(requests_mock):
    yandex = YandexWeatherProvider(api_key="test", base_url="https://yandex.test/forecast")
    openmeteo = OpenMeteoProvider(base_url="https://openmeteo.test")
    service = WeatherService(local_station=None, primary_provider=yandex, fallback_provider=openmeteo)

    requests_mock.get(
        "https://yandex.test/forecast",
        json={
            "fact": {"temp": 5, "pressure_mm": 745, "wind_speed": 4, "precipitation": 0},
        },
    )

    first = service.get_current(1.0, 1.0)
    second = service.get_current(1.0, 1.0)

    assert first.temperature_c == second.temperature_c == 5
    assert requests_mock.call_count == 1


def test_weather_service_cache_expiry(requests_mock):
    controller = TimeController()
    cache = WeatherCache(time_func=controller)
    yandex = YandexWeatherProvider(api_key="test", base_url="https://yandex.test/forecast")
    openmeteo = OpenMeteoProvider(base_url="https://openmeteo.test")
    service = WeatherService(local_station=None, primary_provider=yandex, fallback_provider=openmeteo, cache=cache)

    requests_mock.get(
        "https://yandex.test/forecast",
        json={
            "fact": {"temp": 7, "pressure_mm": 740, "wind_speed": 3, "precipitation": 0},
        },
    )

    service.get_current(1.0, 1.0)
    assert requests_mock.call_count == 1

    controller.advance(WeatherService.CURRENT_TTL + 1)

    service.get_current(1.0, 1.0)
    assert requests_mock.call_count == 2


def test_weather_service_all_providers_fail(requests_mock):
    yandex = YandexWeatherProvider(api_key="test", base_url="https://yandex.test/forecast")
    openmeteo = OpenMeteoProvider(base_url="https://openmeteo.test")
    service = WeatherService(local_station=None, primary_provider=yandex, fallback_provider=openmeteo)

    requests_mock.get("https://yandex.test/forecast", status_code=500, text="server error")
    requests_mock.get("https://openmeteo.test", status_code=502, text="bad gateway")

    with pytest.raises(ProviderError):
        service.get_current(1.0, 1.0)
