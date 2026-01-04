from __future__ import annotations

from datetime import datetime, timezone

from django.core.cache import cache

from backend.core.abstractions import WeatherPoint, WeatherProvider
from backend.core.services.weather_service import WeatherServiceBridge, WeatherServiceError


class _DummyProvider(WeatherProvider):
    name = "dummy"

    def __init__(self) -> None:
        self.calls = 0

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:
        self.calls += 1
        return WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            temperature_c=1.0,
            pressure_hpa=1010.0,
            wind_speed_ms=2.0,
            precipitation_mm=0.1,
            source=self.name,
            observed_at=datetime.now(tz=timezone.utc),
        )


class _FailingProvider(WeatherProvider):
    name = "failing"

    def get_weather(self, latitude: float, longitude: float) -> WeatherPoint:
        raise RuntimeError("boom")


def test_weather_service_caches_results() -> None:
    cache.clear()
    provider = _DummyProvider()
    service = WeatherServiceBridge([provider], cache=cache, ttl=60)

    first = service.get_weather(10.0, 20.0)
    second = service.get_weather(10.0, 20.0)

    assert provider.calls == 1
    assert first.temperature_c == second.temperature_c


def test_weather_service_uses_fallback_provider() -> None:
    cache.clear()
    fallback = _DummyProvider()
    service = WeatherServiceBridge([_FailingProvider(), fallback], cache=cache, ttl=60)

    result = service.get_weather(0.0, 0.0)

    assert fallback.calls == 1
    assert result.temperature_c == 1.0


def test_weather_service_raises_when_all_fail() -> None:
    cache.clear()
    service = WeatherServiceBridge([_FailingProvider()], cache=cache, ttl=60)

    try:
        service.get_weather(0.0, 0.0)
    except WeatherServiceError:
        assert True
    else:  # pragma: no cover
        raise AssertionError("expected WeatherServiceError")
