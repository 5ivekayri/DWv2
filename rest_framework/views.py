"""APIView stub."""
from __future__ import annotations

from typing import Any, Callable, Type


class APIView:
    permission_classes: list[Any] = []

    @classmethod
    def as_view(cls) -> Callable:
        def view(request, *args, **kwargs):
            self = cls()
            handler = getattr(self, request.method.lower(), None)
            if handler is None:
                raise NotImplementedError(f"Method {request.method} not implemented")
            return handler(request, *args, **kwargs)

        return view

    def get(self, request, *args, **kwargs):  # pragma: no cover - interface definition
        raise NotImplementedError
