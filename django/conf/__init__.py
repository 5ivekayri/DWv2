"""Configuration helpers for the Django stub."""
from __future__ import annotations

from typing import Any


class _Settings:
    def __init__(self) -> None:
        self._wrapped: Any | None = None

    def _setup(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def __getattr__(self, item: str) -> Any:
        if self._wrapped is None:
            raise RuntimeError("Settings are not configured")
        return getattr(self._wrapped, item)

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            setattr(self._wrapped, key, value)


settings = _Settings()
