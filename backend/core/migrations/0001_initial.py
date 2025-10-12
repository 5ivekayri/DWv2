"""Initial schema creation for stations and observations."""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional for compatibility with Django migrations
    from sqlalchemy.engine import Engine  # type: ignore
except Exception:  # pragma: no cover
    Engine = Any  # type: ignore

from backend.core import models


def run(engine: Engine | Any | None = None) -> None:
    """Apply the initial schema."""
    models.run_migrations()
