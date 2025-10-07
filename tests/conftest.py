from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import django


def pytest_configure() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")
    django.setup()
