#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
from __future__ import annotations

import os
import sys
import importlib

from django.conf import settings


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    settings_module = importlib.import_module(os.environ["DJANGO_SETTINGS_MODULE"])
    settings._setup(settings_module)
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
