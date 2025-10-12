from __future__ import annotations

import json
import pathlib
import sys
from datetime import timezone

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core import models
from backend.ingest import mqtt_consumer, schemas


@pytest.fixture(autouse=True)
def fresh_database(tmp_path):
    db_url = f"sqlite:///{tmp_path/'test.db'}"
    models.configure_engine(db_url)
    yield


def test_measurement_payload_validation():
    payload = {
        "station_id": "esp32-1",
        "ts_utc": "2024-03-10T12:34:56+00:00",
        "metrics": {
            "temperature_c": 21.5,
            "humidity": 42.0,
            "pressure_hpa": 1005.3,
        },
        "station": {
            "name": "Balcony",
            "latitude": 55.75,
            "longitude": 37.61,
        },
        "extra": {"firmware": "1.2.3"},
    }

    measurement = schemas.MeasurementPayload.parse_obj(payload)

    assert measurement.station_id == "esp32-1"
    assert measurement.temperature_c == 21.5
    assert measurement.humidity_percent == 42.0
    assert measurement.station.name == "Balcony"
    assert measurement.ts_utc.tzinfo == timezone.utc


def test_process_payload_inserts_and_deduplicates():
    topic = "weather/stations/esp32-1/measurements"
    body = {
        "ts_utc": "2024-03-10T12:34:56Z",
        "metrics": {
            "temperature_c": 20.1,
            "humidity_percent": 40.0,
        },
        "station": {
            "name": "Balcony",
            "latitude": 55.75,
            "longitude": 37.61,
        },
    }

    payload = json.dumps(body).encode("utf-8")
    session_factory = models.get_session_factory()

    inserted_first = mqtt_consumer.process_payload(topic, payload, session_factory=session_factory)
    inserted_second = mqtt_consumer.process_payload(topic, payload, session_factory=session_factory)

    assert inserted_first is True
    assert inserted_second is False

    with models.session_scope(session_factory) as session:
        station_count = models.count_stations(session)
        observation_count = models.count_observations(session)

    assert station_count == 1
    assert observation_count == 1
