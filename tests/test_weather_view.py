from __future__ import annotations

from django.test import Client


def test_weather_endpoint_returns_payload() -> None:
    client = Client()
    response = client.get("/api/weather", {"lat": "55.75", "lon": "37.61"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["latitude"] == 55.75
    assert payload["longitude"] == 37.61
    assert "temperature_c" in payload
    assert payload["observed_at"].endswith("Z")


def test_weather_endpoint_validates_params() -> None:
    client = Client()
    response = client.get("/api/weather", {"lat": "abc", "lon": "37.61"})

    assert response.status_code == 400
    assert "detail" in response.json()
