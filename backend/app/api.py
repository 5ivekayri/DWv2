"""Minimal HTTP-like surface for the admin health endpoint.

The tests interact with :class:`HealthAPI` directly instead of going through a
framework.  This keeps the kata lightweight while still modelling the "GET
/api/admin/health" contract described in the requirements.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Mapping, Optional

from backend.core.health import HealthRegistry


@dataclass
class Response:
    status_code: int
    body: str
    headers: Mapping[str, str]


class HealthAPI:
    """Serve health information for the admin UI."""

    HEALTH_PATH = "/api/admin/health"

    def __init__(self, registry: Optional[HealthRegistry] = None) -> None:
        self._registry = registry or HealthRegistry()

    @property
    def registry(self) -> HealthRegistry:
        return self._registry

    # -- HTTP like helpers --------------------------------------------------
    def handle_request(self, method: str, path: str) -> Response:
        method = method.upper()
        if path != self.HEALTH_PATH:
            return Response(status_code=404, body=json.dumps({"detail": "Not found"}), headers={"Content-Type": "application/json"})
        if method != "GET":
            return Response(status_code=405, body=json.dumps({"detail": "Method not allowed"}), headers={"Content-Type": "application/json"})
        payload = self._registry.snapshot()
        return Response(
            status_code=200,
            body=json.dumps(payload, sort_keys=True),
            headers={"Content-Type": "application/json"},
        )

    def get_admin_health(self) -> Dict[str, object]:
        """Convenience method returning the parsed payload."""
        return self._registry.snapshot()

