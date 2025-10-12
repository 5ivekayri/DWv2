"""Lightweight HTTP client compatible with the subset of `requests` we need."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional


class RequestException(Exception):
    """Base exception for HTTP request errors."""


class HTTPError(RequestException):
    def __init__(self, response: "Response") -> None:
        super().__init__(f"HTTP {response.status_code}")
        self.response = response


class Response:
    def __init__(
        self,
        status_code: int,
        content: bytes,
        headers: Optional[Dict[str, str]] = None,
        url: str | None = None,
    ) -> None:
        self.status_code = status_code
        self._content = content
        self.headers = headers or {}
        self.url = url or ""

    @property
    def content(self) -> bytes:
        return self._content

    def json(self) -> Any:
        if not self._content:
            return None
        return json.loads(self._content.decode("utf-8"))

    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            raise HTTPError(self)


from .sessions import Session  # noqa: E402  (import after class definitions)


def request(method: str, url: str, **kwargs: Any) -> Response:
    with Session() as session:
        return session.request(method, url, **kwargs)


def post(url: str, **kwargs: Any) -> Response:
    return request("POST", url, **kwargs)


__all__ = [
    "RequestException",
    "HTTPError",
    "Response",
    "Session",
    "request",
    "post",
]
