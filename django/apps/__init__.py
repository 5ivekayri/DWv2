"""App configuration stub."""
from __future__ import annotations


class AppConfig:
    def __init__(self, name: str, app_name: str | None = None) -> None:
        self.name = name
        self.app_name = app_name or name.split(".")[-1]
        self.label = self.app_name.replace(".", "_")

    def ready(self) -> None:  # pragma: no cover - hook for completeness
        """Placeholder for startup hooks."""
        return None
