from __future__ import annotations

import pytest

from requests_mock import Mocker


@pytest.fixture
def requests_mock():
    with Mocker() as mock:
        yield mock
