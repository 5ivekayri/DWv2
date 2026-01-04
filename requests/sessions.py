from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from . import HTTPError, RequestException, Response


class Session:
    transport = None

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        data: bytes | None = None,
        timeout: Optional[float] = None,
    ) -> Response:
        method = method.upper()
        if params:
            query = urllib.parse.urlencode(params)
            delimiter = "&" if "?" in url else "?"
            url = f"{url}{delimiter}{query}"
        transport = getattr(self, "transport", None)
        if transport:
            return transport(method=method, url=url, timeout=timeout)
        payload = data
        request_headers = dict(headers or {})
        if json is not None:
            payload = json.dumps(json).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read()
                return Response(resp.getcode(), content, dict(resp.headers), url)
        except urllib.error.HTTPError as exc:  # pragma: no cover - network not hit in tests
            content = exc.read()
            response = Response(exc.code, content, dict(exc.headers or {}), url)
            raise HTTPError(response) from None
        except urllib.error.URLError as exc:  # pragma: no cover - network not hit in tests
            raise RequestException(str(exc)) from exc

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def close(self) -> None:  # pragma: no cover - nothing to clean up
        return None

    def __enter__(self) -> "Session":  # pragma: no cover - used implicitly in helpers
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - nothing to close
        self.close()


__all__ = ["Session"]
