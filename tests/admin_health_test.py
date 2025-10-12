import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

# Ensure the repository root is importable when tests are executed from an
# arbitrary working directory (mirrors how CI runs the suite).
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.api import HealthAPI
from backend.core.health import HealthRegistry


@pytest.fixture()
def registry() -> HealthRegistry:
    registry = HealthRegistry()
    now = datetime(2024, 1, 10, 12, 30, tzinfo=timezone.utc)
    registry.record_station_heartbeat("station-1", now)
    registry.record_station_heartbeat("station-2", now - timedelta(minutes=5))
    registry.record_provider_error("yandex-weather")
    registry.record_provider_error("open-meteo", increment=3)
    registry.set_cache_stats({"hits": 42, "misses": 3, "keys": 7})
    return registry


def test_health_endpoint_returns_expected_payload(registry: HealthRegistry) -> None:
    api = HealthAPI(registry)
    response = api.handle_request("GET", "/api/admin/health")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

    payload = json.loads(response.body)
    assert payload["providers"] == {"open-meteo": 3, "yandex-weather": 1}
    assert payload["cache"] == {"hits": 42, "misses": 3, "keys": 7}
    assert set(payload["stations"].keys()) == {"station-1", "station-2"}


def test_health_endpoint_rejects_unknown_path(registry: HealthRegistry) -> None:
    api = HealthAPI(registry)
    response = api.handle_request("GET", "/api/admin/unknown")

    assert response.status_code == 404
    assert json.loads(response.body)["detail"].lower().startswith("not")


def test_provider_errors_can_be_drained(registry: HealthRegistry) -> None:
    drained = registry.drain_provider_errors()
    assert drained == {"yandex-weather": 1, "open-meteo": 3}
    assert registry.snapshot()["providers"] == {}


def test_non_get_is_rejected(registry: HealthRegistry) -> None:
    api = HealthAPI(registry)
    response = api.handle_request("POST", "/api/admin/health")

    assert response.status_code == 405
    assert "method" in json.loads(response.body)["detail"].lower()
