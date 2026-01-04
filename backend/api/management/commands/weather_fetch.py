"""Management command to fetch weather using the same stack as the API."""
from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from backend.api.views import _serialize_point, _stub_weather, get_weather_service
from backend.core.services.weather_service import WeatherServiceError


class Command(BaseCommand):
    help = "Fetch current weather for the provided coordinates"

    def add_arguments(self, parser) -> None:  # noqa: D401
        parser.add_argument("--lat", type=float, help="Latitude")
        parser.add_argument("--lon", type=float, help="Longitude")
        parser.add_argument("--city", type=str, help="City name (only city=test stub is supported)")

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: D401
        city = options.get("city")
        latitude = options.get("lat")
        longitude = options.get("lon")

        if city:
            if city != "test":
                raise CommandError("Only city=test stub is supported")
            point = _stub_weather()
        else:
            if latitude is None or longitude is None:
                raise CommandError("--lat and --lon are required unless using city=test")
            try:
                point = get_weather_service().get_weather(latitude=latitude, longitude=longitude)
            except WeatherServiceError as exc:
                raise CommandError("All weather providers failed") from exc

        payload = _serialize_point(point)
        self.stdout.write(json.dumps(payload))
