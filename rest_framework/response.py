"""Response helper."""
from __future__ import annotations

from typing import Any, Dict


class Response:
    def __init__(self, data: Any, status: int = 200, headers: Dict[str, str] | None = None) -> None:
        self.data = data
        self.status = status
        self.headers = headers or {}
