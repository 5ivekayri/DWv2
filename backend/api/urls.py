"""API URL configuration."""
from __future__ import annotations

from django.urls import path

from backend.api.views import WeatherView

urlpatterns = [
    path("weather", WeatherView.as_view(), name="weather"),
]
