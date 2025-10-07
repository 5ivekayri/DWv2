"""REST API views for weather information."""
from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from django.conf import settings
from django.core.cache import caches
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.core.providers.localstation import LocalStationProvider
from backend.core.providers.openmeteo import OpenMeteoProvider
from backend.core.providers.yandex import YandexWeatherProvider
from backend.core.services.weather_service import WeatherServiceBridge


@lru_cache(maxsize=1)
def get_weather_service() -> WeatherServiceBridge:
    cache_backend = caches[settings.WEATHER_CACHE_ALIAS]
    providers = (
        YandexWeatherProvider(),
        OpenMeteoProvider(),
        LocalStationProvider(),
    )
    return WeatherServiceBridge(
        providers=providers,
        cache=cache_backend,
        ttl=settings.WEATHER_CACHE_TIMEOUT,
    )


class WeatherView(APIView):
    """Provide normalized weather data for requested coordinates."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):  # noqa: D401
        """Return the weather snapshot for the specified coordinates."""
        try:
            latitude = float(request.query_params["lat"])
            longitude = float(request.query_params["lon"])
        except KeyError:
            return Response({"detail": "lat and lon query parameters are required"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"detail": "lat and lon must be valid floating point numbers"}, status=status.HTTP_400_BAD_REQUEST)

        point = get_weather_service().get_weather(latitude=latitude, longitude=longitude)
        payload = asdict(point)
        payload["observed_at"] = point.observed_at.astimezone(settings.DEFAULT_TIMEZONE).isoformat().replace("+00:00", "Z")
        return Response(payload, status=status.HTTP_200_OK)
