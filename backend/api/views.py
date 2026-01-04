"""REST API views for weather information."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
import os

from django.conf import settings
from django.core.cache import caches
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.core.abstractions import WeatherPoint
from backend.core.providers.openmeteo import OpenMeteoProvider
from backend.core.providers.openweather import OpenWeatherProvider
from backend.core.providers.yandex import YandexWeatherProvider
from backend.core.services.weather_service import WeatherServiceBridge, WeatherServiceError


@lru_cache(maxsize=1)
def get_weather_service() -> WeatherServiceBridge:
    cache_backend = caches[settings.WEATHER_CACHE_ALIAS]
    providers = _build_providers()
    return WeatherServiceBridge(
        providers=providers,
        cache=cache_backend,
        ttl=settings.WEATHER_CACHE_TIMEOUT,
    )


def _build_providers() -> tuple:
    providers = []
    openweather_key = os.environ.get("OPENWEATHER_API_KEY")
    if openweather_key:
        providers.append(OpenWeatherProvider(api_key=openweather_key))

    yandex_key = os.environ.get("YANDEX_WEATHER_KEY")
    if yandex_key:
        providers.append(YandexWeatherProvider(api_key=yandex_key))

    providers.append(OpenMeteoProvider())
    return tuple(providers)


def reset_weather_service_cache() -> None:
    get_weather_service.cache_clear()


def _stub_weather() -> WeatherPoint:
    return WeatherPoint(
        latitude=0.0,
        longitude=0.0,
        temperature_c=20.0,
        pressure_hpa=1013.0,
        wind_speed_ms=3.0,
        precipitation_mm=0.0,
        source="stub",
        observed_at=datetime(2024, 1, 1, tzinfo=settings.DEFAULT_TIMEZONE),
    )


def _serialize_point(point: WeatherPoint) -> dict:
    payload = asdict(point)
    payload["observed_at"] = point.observed_at.astimezone(settings.DEFAULT_TIMEZONE).isoformat().replace("+00:00", "Z")
    return payload


class WeatherView(APIView):
    """Provide normalized weather data for requested coordinates."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):  # noqa: D401
        """Return the weather snapshot for the specified coordinates."""
        city = request.query_params.get("city")
        if city:
            if city != "test":
                return Response({"detail": "only city=test stub is supported"}, status=status.HTTP_400_BAD_REQUEST)
            point = _stub_weather()
        else:
            try:
                latitude = float(request.query_params["lat"])
                longitude = float(request.query_params["lon"])
            except KeyError:
                return Response(
                    {"detail": "lat and lon query parameters are required"}, status=status.HTTP_400_BAD_REQUEST
                )
            except ValueError:
                return Response(
                    {"detail": "lat and lon must be valid floating point numbers"}, status=status.HTTP_400_BAD_REQUEST
                )

            try:
                point = get_weather_service().get_weather(latitude=latitude, longitude=longitude)
            except WeatherServiceError:
                return Response(
                    {"detail": "All weather providers failed. Please try again later."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
        payload = _serialize_point(point)
        return Response(payload, status=status.HTTP_200_OK)
