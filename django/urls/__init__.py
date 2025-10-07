"""URL routing helpers for the Django stub."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence


@dataclass
class URLPattern:
    route: str
    view: Any
    name: str | None = None


def path(route: str, view: Any, name: str | None = None) -> URLPattern:
    return URLPattern(route=route, view=view, name=name)


def include(module: str | Sequence[URLPattern]) -> List[URLPattern]:
    if isinstance(module, (list, tuple)):
        return list(module)
    imported = importlib.import_module(module)
    return list(getattr(imported, "urlpatterns"))


def resolve(urlpatterns: Iterable[URLPattern], path: str):
    segments = [segment for segment in path.strip("/").split("/") if segment]
    return _resolve(urlpatterns, segments)


def _resolve(urlpatterns: Iterable[URLPattern], segments: List[str]):
    for pattern in urlpatterns:
        route_segments = [segment for segment in pattern.route.strip("/").split("/") if segment]
        if isinstance(pattern.view, list):
            if segments[: len(route_segments)] != route_segments:
                continue
            remainder = segments[len(route_segments) :]
            result = _resolve(pattern.view, remainder)
            if result:
                return result
        else:
            if segments == route_segments:
                return pattern.view
    return None
