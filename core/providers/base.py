from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

import requests
from requests import Response


logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Base provider error."""


class QuotaExceeded(ProviderError):
    """Raised when a provider reports a quota/usage limit issue."""


@dataclass
class RequestConfig:
    timeout: float = 5.0
    retries: int = 2
    backoff_factor: float = 0.3
    status_forcelist: Iterable[int] = (429, 500, 502, 503, 504)


class WeatherProvider:
    """Base class that adds retry/timeouts for HTTP providers."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        request_config: Optional[RequestConfig] = None,
    ) -> None:
        self.request_config = request_config or RequestConfig()
        self.session = session or self._build_session(self.request_config)
        self._log = logging.getLogger(self.__class__.__name__)

    def _build_session(self, config: RequestConfig) -> requests.Session:
        return requests.Session()

    def _handle_response(self, response: Response) -> Response:
        if response.status_code == 429:
            self._log.warning("Quota exceeded: %s", response.text)
            raise QuotaExceeded("quota exceeded")
        if response.status_code >= 400:
            self._log.error("Provider returned %s: %s", response.status_code, response.text)
            raise ProviderError(f"HTTP {response.status_code}")
        return response

    def _request(self, method: str, url: str, **kwargs) -> Response:
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.request_config.timeout,
                **kwargs,
            )
        except requests.Timeout as exc:
            self._log.error("Request timed out", exc_info=exc)
            raise ProviderError("timeout") from exc
        except requests.RequestException as exc:  # pragma: no cover - safety
            self._log.error("Request failed", exc_info=exc)
            raise ProviderError("request failed") from exc
        return self._handle_response(response)


__all__ = ["WeatherProvider", "ProviderError", "QuotaExceeded", "RequestConfig"]
