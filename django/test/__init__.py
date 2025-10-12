"""Testing utilities for the Django stub."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from django.conf import settings
from django.urls import resolve


class Response:
    def __init__(self, data: Any, status_code: int, headers: Dict[str, str] | None = None) -> None:
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> Any:
        return self.data


class Client:
    """Very small test client capable of GET requests."""

    def get(self, path: str, data: Dict[str, Any] | None = None) -> Response:
        if not hasattr(settings, "ROOT_URLCONF"):
            raise RuntimeError("ROOT_URLCONF is not configured")
        urlconf = __import__(settings.ROOT_URLCONF, fromlist=["urlpatterns"])
        view = resolve(getattr(urlconf, "urlpatterns"), path)
        if view is None:
            return Response({"detail": "not found"}, status_code=404)
        request = SimpleNamespace(query_params=data or {}, data={}, method="GET")
        result = view(request)
        return Response(getattr(result, "data", result), getattr(result, "status", 200), getattr(result, "headers", {}))
