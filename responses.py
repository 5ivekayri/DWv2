"""Lightweight stand-in for the `responses` package used in tests."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest import mock

import requests


@dataclass
class _FakeRequest:
    method: str
    url: str
    body: Any
    headers: Dict[str, Any]
    kwargs: Dict[str, Any]


@dataclass
class Call:
    request: _FakeRequest
    response: requests.Response


class RequestsMock:
    """Minimal requests mocker with the same API surface used in tests."""

    def __init__(self) -> None:
        self._registry: List[Dict[str, Any]] = []
        self._patcher: Optional[mock._patch] = None
        self.calls: List[Call] = []

    def add(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        body: Any = None,
        status: int = 200,
    ) -> None:
        self._registry.append(
            {
                "method": method.upper(),
                "url": url,
                "json": json,
                "body": body,
                "status": status,
            }
        )

    def _handle_request(
        self,
        session: requests.sessions.Session,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        for entry in self._registry:
            if entry["method"] == method.upper() and entry["url"] == url:
                payload = entry["body"]
                headers: Dict[str, Any] = {}
                if entry["json"] is not None:
                    payload = json.dumps(entry["json"])
                    headers["Content-Type"] = "application/json"
                if payload is None:
                    payload = ""
                if isinstance(payload, str):
                    content_bytes = payload.encode("utf-8")
                else:
                    content_bytes = payload
                response = requests.Response(entry["status"], content_bytes, headers, url)
                fake_request = _FakeRequest(
                    method=method.upper(),
                    url=url,
                    body=kwargs.get("json", kwargs.get("data")),
                    headers=kwargs.get("headers", {}),
                    kwargs=kwargs,
                )
                self.calls.append(Call(fake_request, response))
                return response
        raise AssertionError(f"Unexpected request {method.upper()} {url}")

    def __enter__(self) -> "RequestsMock":
        def wrapper(session: requests.sessions.Session, method: str, url: str, **kwargs: Any) -> requests.Response:
            return self._handle_request(session, method, url, **kwargs)

        self._patcher = mock.patch("requests.sessions.Session.request", new=wrapper)
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._patcher:
            self._patcher.stop()
        self._patcher = None
        self._registry.clear()


def activate(func):  # pragma: no cover - not used in the tests but provided for parity
    def wrapper(*args: Any, **kwargs: Any):
        with RequestsMock() as rsps:
            return func(rsps, *args, **kwargs)

    return wrapper


__all__ = ["RequestsMock", "Call", "activate"]
