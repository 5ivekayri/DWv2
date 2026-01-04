from __future__ import annotations

import os

import django
import pytest
import requests_mock as requests_mock_lib


os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
os.environ.setdefault("TESTING_MODE", "1")

django.setup()


@pytest.fixture()
def requests_mock():
    with requests_mock_lib.Mocker() as mocker:
        yield mocker
