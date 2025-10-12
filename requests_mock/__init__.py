from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import requests


@dataclass
class _RegisteredResponse:
    method: str
    url: str
    response: requests.Response
    repeatable: bool = True


class _Transport:
    def __init__(self) -> None:
        self._responses: List[_RegisteredResponse] = []
        self.call_count = 0

    def register(
        self,
        method: str,
        url: str,
        *,
        json: Any | None = None,
        status_code: int = 200,
        text: str | None = None,
    ) -> None:
        response = requests.Response(status_code=status_code, json_data=json, text=text)
        self._responses.append(_RegisteredResponse(method=method.upper(), url=url, response=response))

    def __call__(self, *, method: str, url: str, timeout: Optional[float] = None, **kwargs) -> requests.Response:
        self.call_count += 1
        for registered in self._responses:
            if registered.method == method and registered.url == url:
                return registered.response
        raise AssertionError(f"No mock registered for {method} {url}")

    def reset(self) -> None:
        self._responses.clear()
        self.call_count = 0


class Mocker(AbstractContextManager):
    def __init__(self) -> None:
        self.transport = _Transport()

    def __enter__(self) -> "Mocker":
        self._previous_transport = requests.Session.transport
        requests.Session.transport = self.transport
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        requests.Session.transport = self._previous_transport
        self.transport.reset()

    # API similar to real library
    def get(self, url: str, *, json: Any | None = None, status_code: int = 200, text: str | None = None):
        self.transport.register("GET", url, json=json, status_code=status_code, text=text)

    def post(self, url: str, *, json: Any | None = None, status_code: int = 200, text: str | None = None):
        self.transport.register("POST", url, json=json, status_code=status_code, text=text)

    @property
    def call_count(self) -> int:
        return self.transport.call_count


__all__ = ["Mocker"]
