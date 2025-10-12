"""Minimal stub of Django required for the kata environment."""
from __future__ import annotations

import importlib
import os
from types import SimpleNamespace

from django.conf import settings as conf_settings
from django.core.cache import caches

__all__ = ["setup"]


def setup() -> None:
    module_name = os.environ.get("DJANGO_SETTINGS_MODULE")
    if not module_name:
        raise RuntimeError("DJANGO_SETTINGS_MODULE is not set")

    module = importlib.import_module(module_name)
    payload = {
        name: getattr(module, name)
        for name in dir(module)
        if name.isupper()
    }
    conf_settings._setup(SimpleNamespace(**payload))

    cache_config = getattr(conf_settings, "CACHES", None)
    caches.configure(cache_config)
