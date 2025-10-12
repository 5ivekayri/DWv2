"""Payload schemas for MQTT ingestion with optional Pydantic support."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional during tests
    from pydantic import BaseModel, Field, root_validator, validator
    HAVE_PYDANTIC = True
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    Field = lambda default=None, **_: default  # type: ignore
    root_validator = validator = None  # type: ignore
    HAVE_PYDANTIC = False

__all__ = ["MeasurementPayload", "StationMetadata"]


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("ts_utc must be timezone aware (UTC)")
    return dt.astimezone(timezone.utc)


def _normalise_payload(values: Dict[str, Any]) -> Dict[str, Any]:
    raw = dict(values)
    metrics = values.get("metrics") or {}
    for field in (
        "temperature_c",
        "humidity_percent",
        "pressure_hpa",
        "wind_speed_ms",
        "wind_direction_deg",
        "rainfall_mm",
    ):
        if values.get(field) is not None:
            continue
        if field == "humidity_percent":
            for candidate in ("humidity", "humidity_percent"):
                if candidate in metrics:
                    values["humidity_percent"] = metrics[candidate]
                    break
            else:
                if "humidity" in values:
                    values["humidity_percent"] = values["humidity"]
            continue
        if field in metrics:
            values[field] = metrics[field]

    station_payload = values.get("station") or {}
    if not isinstance(station_payload, dict):
        station_payload = {}
    if values.get("station_name") and "name" not in station_payload:
        station_payload["name"] = values["station_name"]
    if values.get("station_id") and "id" not in station_payload:
        station_payload["id"] = values["station_id"]
    values["station"] = station_payload
    values["raw"] = raw
    return values


class _MeasurementMixin:
    def station_defaults(self) -> Dict[str, Any]:
        return {
            "name": self.station.name,
            "latitude": self.station.latitude,
            "longitude": self.station.longitude,
            "elevation_m": self.station.elevation_m,
            "meta": self.station.meta if self.station.meta is not None else {},
        }

    def to_observation_dict(self) -> Dict[str, Any]:
        return {
            "ts_utc": self.ts_utc,
            "temperature_c": self.temperature_c,
            "humidity_percent": self.humidity_percent,
            "pressure_hpa": self.pressure_hpa,
            "wind_speed_ms": self.wind_speed_ms,
            "wind_direction_deg": self.wind_direction_deg,
            "rainfall_mm": self.rainfall_mm,
            "raw_payload": self.raw,
        }


if HAVE_PYDANTIC:

    class StationMetadata(BaseModel):
        id: Optional[str] = Field(default=None)
        name: Optional[str] = Field(default=None)
        latitude: Optional[float] = Field(default=None)
        longitude: Optional[float] = Field(default=None)
        elevation_m: Optional[float] = Field(default=None)
        meta: Dict[str, Any] = Field(default_factory=dict)

    class MeasurementPayload(_MeasurementMixin, BaseModel):
        station_id: str = Field(...)
        ts_utc: datetime = Field(...)
        temperature_c: Optional[float] = Field(default=None)
        humidity_percent: Optional[float] = Field(default=None)
        pressure_hpa: Optional[float] = Field(default=None)
        wind_speed_ms: Optional[float] = Field(default=None)
        wind_direction_deg: Optional[float] = Field(default=None)
        rainfall_mm: Optional[float] = Field(default=None)
        station: StationMetadata = Field(default_factory=StationMetadata)
        raw: Dict[str, Any] = Field(default_factory=dict)

        class Config:
            allow_population_by_field_name = True

        @root_validator(pre=True)
        def _apply_normalisation(cls, values: Dict[str, Any]):
            return _normalise_payload(values)

        @validator("ts_utc", pre=True)
        def _validate_ts(cls, value: Any) -> datetime:
            return _ensure_datetime(value)

else:

    @dataclass
    class StationMetadata:
        id: Optional[str] = None
        name: Optional[str] = None
        latitude: Optional[float] = None
        longitude: Optional[float] = None
        elevation_m: Optional[float] = None
        meta: Dict[str, Any] = field(default_factory=dict)

    class MeasurementPayload(_MeasurementMixin):
        def __init__(
            self,
            *,
            station_id: str,
            ts_utc: datetime,
            temperature_c: Optional[float] = None,
            humidity_percent: Optional[float] = None,
            pressure_hpa: Optional[float] = None,
            wind_speed_ms: Optional[float] = None,
            wind_direction_deg: Optional[float] = None,
            rainfall_mm: Optional[float] = None,
            station: Optional[StationMetadata] = None,
            raw: Optional[Dict[str, Any]] = None,
        ) -> None:
            self.station_id = station_id
            self.ts_utc = ts_utc
            self.temperature_c = temperature_c
            self.humidity_percent = humidity_percent
            self.pressure_hpa = pressure_hpa
            self.wind_speed_ms = wind_speed_ms
            self.wind_direction_deg = wind_direction_deg
            self.rainfall_mm = rainfall_mm
            self.station = station or StationMetadata(id=station_id)
            if self.station.id is None:
                self.station.id = station_id
            self.raw = raw or {}

        @classmethod
        def parse_obj(cls, data: Dict[str, Any]) -> "MeasurementPayload":
            if not isinstance(data, dict):
                raise TypeError("Measurement payload must be a dictionary")
            normalised = _normalise_payload(dict(data))
            if "station_id" not in normalised:
                raise ValueError("station_id is required")
            if "ts_utc" not in normalised:
                raise ValueError("ts_utc is required")
            ts_utc = _ensure_datetime(normalised["ts_utc"])
            station_data = normalised.get("station") or {}
            station_meta = station_data.get("meta") or {}
            station = StationMetadata(
                id=station_data.get("id") or normalised["station_id"],
                name=station_data.get("name"),
                latitude=station_data.get("latitude"),
                longitude=station_data.get("longitude"),
                elevation_m=station_data.get("elevation_m"),
                meta=dict(station_meta),
            )
            return cls(
                station_id=normalised["station_id"],
                ts_utc=ts_utc,
                temperature_c=normalised.get("temperature_c"),
                humidity_percent=normalised.get("humidity_percent"),
                pressure_hpa=normalised.get("pressure_hpa"),
                wind_speed_ms=normalised.get("wind_speed_ms"),
                wind_direction_deg=normalised.get("wind_direction_deg"),
                rainfall_mm=normalised.get("rainfall_mm"),
                station=station,
                raw=normalised.get("raw") or dict(data),
            )
