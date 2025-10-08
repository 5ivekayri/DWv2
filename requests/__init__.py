from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class RequestException(Exception):
    """Base exception for the lightweight requests shim."""


class Timeout(RequestException):
    """Raised when an operation times out."""


class Response:
    def __init__(self, status_code: int = 200, json_data: Any = None, text: str | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text if text is not None else ("" if json_data is None else str(json_data))

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("No JSON data set on response")
        return self._json_data


class Session:
    transport: Optional[Callable[..., Response]] = None

    def __init__(self) -> None:
        self._adapters: Dict[str, Any] = {}

    def mount(self, prefix: str, adapter: Any) -> None:  # pragma: no cover - compatibility
        self._adapters[prefix] = adapter

    def request(self, method: str, url: str, timeout: Optional[float] = None, **kwargs) -> Response:
        if Session.transport is None:
            raise RequestException("No HTTP transport configured")
        return Session.transport(method=method.upper(), url=url, timeout=timeout, **kwargs)


class adapters:  # pragma: no cover - namespace shim
    class HTTPAdapter:
        def __init__(self, max_retries: Any = None) -> None:
            self.max_retries = max_retries


__all__ = [
    "Session",
    "Response",
    "RequestException",
    "Timeout",
]
