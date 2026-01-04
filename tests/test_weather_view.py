from __future__ import annotations

from datetime import datetime

import pytest
from django.test import Client

from backend.api.views import reset_weather_service_cache


@pytest.fixture(autouse=True)
def _reset_service_cache():
    reset_weather_service_cache()
    yield
    reset_weather_service_cache()


def test_weather_endpoint_returns_stub(requests_mock) -> None:
    client = Client()
    response = client.get("/api/weather", {"city": "test"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "stub"
    assert payload["latitude"] == 0.0
    assert payload["longitude"] == 0.0
    assert requests_mock.call_count == 0


def test_weather_endpoint_uses_openmeteo(requests_mock, monkeypatch) -> None:
    client = Client()
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_WEATHER_KEY", raising=False)
    reset_weather_service_cache()

    requests_mock.get(
        "https://api.open-meteo.com/v1/forecast",
        json={
            "current": {
                "time": "2024-01-01T00:00",
                "temperature_2m": 5.5,
                "pressure_msl": 1012.0,
                "wind_speed_10m": 4.0,
                "precipitation": 0.2,
            }
        },
    )

    response = client.get("/api/weather", {"lat": "55.75", "lon": "37.61"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "openmeteo"
    assert payload["temperature_c"] == 5.5
    assert payload["pressure_hpa"] == 1012.0


def test_weather_endpoint_uses_openweather_when_key_present(requests_mock, monkeypatch) -> None:
    client = Client()
    monkeypatch.setenv("OPENWEATHER_API_KEY", "token")
    monkeypatch.delenv("YANDEX_WEATHER_KEY", raising=False)
    reset_weather_service_cache()

    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/weather",
        json={
            "dt": int(datetime(2024, 1, 1).timestamp()),
            "main": {"temp": 12.3, "pressure": 1000},
            "wind": {"speed": 3.2},
            "rain": {"1h": 0.0},
        },
    )

    response = client.get("/api/weather", {"lat": "10", "lon": "20"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "openweather"
    assert payload["temperature_c"] == 12.3
    assert requests_mock.call_count == 1
