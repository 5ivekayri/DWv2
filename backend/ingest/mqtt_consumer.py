"""MQTT consumer that validates payloads and stores them into the database."""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

try:  # pragma: no cover - optional dependency during tests
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - handled lazily
    mqtt = None  # type: ignore

from backend.core import models
from backend.ingest import schemas

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TOPIC = "weather/stations/+/measurements"


@dataclass
class MQTTConfig:
    host: str = os.getenv("MQTT_HOST", "localhost")
    port: int = int(os.getenv("MQTT_PORT", "1883"))
    username: Optional[str] = os.getenv("MQTT_USERNAME")
    password: Optional[str] = os.getenv("MQTT_PASSWORD")
    keepalive: int = int(os.getenv("MQTT_KEEPALIVE", "60"))
    client_id: str = os.getenv("MQTT_CLIENT_ID", f"dwv2-consumer-{uuid4().hex[:8]}")
    session_factory: Optional[models.SessionFactory] = None


class MQTTIngestConsumer:
    """Subscribes to station measurement topic and persists payloads."""

    def __init__(self, config: Optional[MQTTConfig] = None):
        if mqtt is None:
            raise RuntimeError("paho-mqtt must be installed to run the MQTT consumer")
        self.config = config or MQTTConfig()
        self.session_factory = self.config.session_factory or models.get_session_factory()
        self.client = mqtt.Client(client_id=self.config.client_id)
        if self.config.username:
            self.client.username_pw_set(self.config.username, self.config.password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    # -- MQTT callbacks -------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):  # type: ignore[override]
        if rc != 0:
            logger.error("Failed to connect to MQTT broker: rc=%s", rc)
            return
        logger.info("Connected to MQTT broker, subscribing to %s", TOPIC)
        client.subscribe(TOPIC)

    def _on_message(self, client, userdata, msg):  # type: ignore[override]
        try:
            inserted = process_payload(msg.topic, msg.payload, session_factory=self.session_factory)
            if inserted:
                logger.info("Stored observation for topic %s", msg.topic)
            else:
                logger.info("Duplicate observation ignored for topic %s", msg.topic)
        except Exception:  # pragma: no cover - logged for visibility
            logger.exception("Failed to process message from topic %s", msg.topic)

    # -- Public API -----------------------------------------------------
    def start(self):
        self._install_signal_handlers()
        self.client.connect(self.config.host, self.config.port, self.config.keepalive)
        logger.info("Starting MQTT consumer loop")
        self.client.loop_forever()

    def stop(self):
        logger.info("Stopping MQTT consumer loop")
        self.client.disconnect()

    def _install_signal_handlers(self):
        def _handle_signal(signum, frame):
            logger.info("Received signal %s, shutting down", signum)
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)


# ---------------------------------------------------------------------------

def parse_topic_station(topic: str) -> str:
    parts = topic.split("/")
    if len(parts) >= 4 and parts[0] == "weather" and parts[1] == "stations":
        return parts[2]
    raise ValueError(f"Unsupported topic format: {topic}")


def process_payload(topic: str, payload: bytes, session_factory: Optional[models.SessionFactory] = None) -> bool:
    """Validate and store a payload coming from the MQTT broker."""

    station_id = parse_topic_station(topic)
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload for station {station_id}") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object")

    data.setdefault("station_id", station_id)
    measurement = schemas.MeasurementPayload.parse_obj(data)

    observation_data = measurement.to_observation_dict()

    factory = session_factory or models.get_session_factory()
    with models.session_scope(factory) as session:
        station = models.get_or_create_station(
            session,
            external_id=measurement.station_id,
            defaults=measurement.station_defaults(),
        )
        return models.insert_observation(session, station=station, payload=observation_data)


def main():
    consumer = MQTTIngestConsumer()
    consumer.start()


if __name__ == "__main__":
    main()
