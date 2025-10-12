"""Lightweight database helpers for storing weather station observations."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

try:  # Optional import for MySQL support
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:  # pragma: no cover - pymysql is optional
    pymysql = None  # type: ignore
    DictCursor = None  # type: ignore


@dataclass
class Station:
    id: int
    external_id: str
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Observation:
    id: int
    station_id: int
    ts_utc: str
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    rainfall_mm: Optional[float] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


class DatabaseSession:
    """Minimal DB-API session wrapper with context aware placeholders."""

    def __init__(self, connection, placeholder: str):
        self.connection = connection
        self.placeholder = placeholder

    # -- DB-API compatibility -------------------------------------------------
    def _prepare_sql(self, sql: str) -> str:
        if self.placeholder == "?":
            return sql
        return sql.replace("?", self.placeholder)

    def execute(self, sql: str, params: tuple = ()):
        cursor = self.connection.cursor()
        cursor.execute(self._prepare_sql(sql), params)
        return cursor

    def fetchone(self, sql: str, params: tuple = ()):
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        return row

    def fetchall(self, sql: str, params: tuple = ()):
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


class SessionFactory:
    def __init__(self, url: str, placeholder: str, driver: str):
        self.url = url
        self.placeholder = placeholder
        self.driver = driver

    def __call__(self) -> DatabaseSession:
        connection = create_connection(self.url, self.driver)
        return DatabaseSession(connection, self.placeholder)


_engine_lock = threading.Lock()
_database_url: Optional[str] = None
_session_factory: Optional[SessionFactory] = None
_driver: Optional[str] = None
_placeholder: str = "?"


# ---------------------------------------------------------------------------

def _default_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./dwv2.db")


def configure_engine(url: Optional[str] = None, **_: Any) -> str:
    """Configure database access using the provided URL."""

    global _database_url, _session_factory, _driver, _placeholder
    with _engine_lock:
        _database_url = url or _default_database_url()
        driver, placeholder = detect_driver(_database_url)
        _driver = driver
        _placeholder = placeholder
        _session_factory = SessionFactory(_database_url, _placeholder, _driver)
    run_migrations()
    return _database_url


def detect_driver(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme.startswith("mysql"):
        if pymysql is None:
            raise RuntimeError("PyMySQL is required for MySQL connections")
        return "mysql", "%s"
    if parsed.scheme.startswith("sqlite") or parsed.scheme == "":
        return "sqlite", "?"
    raise ValueError(f"Unsupported database scheme: {parsed.scheme}")


def create_connection(url: str, driver: str):
    parsed = urlparse(url)
    if driver == "sqlite":
        path = unquote(parsed.path or parsed.netloc or ":memory:")
        if path.startswith("/"):
            db_path = path
        else:
            db_path = os.path.abspath(path)
        connection = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    if driver == "mysql":
        assert pymysql is not None and DictCursor is not None
        params = {
            "host": parsed.hostname or "localhost",
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/") or None,
            "port": parsed.port or 3306,
            "cursorclass": DictCursor,
            "autocommit": False,
        }
        return pymysql.connect(**params)

    raise ValueError(f"Unsupported driver: {driver}")


def get_session_factory() -> SessionFactory:
    global _session_factory
    if _session_factory is None:
        configure_engine()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope(session_factory: Optional[SessionFactory] = None):
    factory = session_factory or get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------

def run_migrations() -> None:
    factory = get_session_factory()
    session = factory()
    try:
        session.execute(
            """
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id VARCHAR(128) NOT NULL UNIQUE,
                name VARCHAR(255),
                latitude REAL,
                longitude REAL,
                elevation_m REAL,
                meta TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        session.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id INTEGER NOT NULL,
                ts_utc TEXT NOT NULL,
                temperature_c REAL,
                humidity_percent REAL,
                pressure_hpa REAL,
                wind_speed_ms REAL,
                wind_direction_deg REAL,
                rainfall_mm REAL,
                raw_payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE CASCADE
            )
            """
        )
        session.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_observation_station_ts
            ON observations (station_id, ts_utc)
            """
        )
        session.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_observations_station_ts
            ON observations (station_id, ts_utc)
            """
        )
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_meta(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return dict(value)
    try:
        return json.loads(value)
    except Exception:
        return {}


def _station_from_row(row) -> Station:
    return Station(
        id=row["id"],
        external_id=row["external_id"],
        name=row.get("name") if isinstance(row, dict) else row["name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        elevation_m=row["elevation_m"],
        meta=_decode_meta(row["meta"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _observation_from_row(row) -> Observation:
    return Observation(
        id=row["id"],
        station_id=row["station_id"],
        ts_utc=row["ts_utc"],
        temperature_c=row["temperature_c"],
        humidity_percent=row["humidity_percent"],
        pressure_hpa=row["pressure_hpa"],
        wind_speed_ms=row["wind_speed_ms"],
        wind_direction_deg=row["wind_direction_deg"],
        rainfall_mm=row["rainfall_mm"],
        raw_payload=_decode_meta(row["raw_payload"]),
        created_at=row["created_at"],
    )


def get_or_create_station(
    session: DatabaseSession,
    *,
    external_id: str,
    defaults: Optional[Dict[str, Any]] = None,
) -> Station:
    defaults = defaults or {}
    row = session.fetchone(
        "SELECT * FROM stations WHERE external_id = ?",
        (external_id,),
    )
    now = utcnow_iso()
    if row:
        station = _station_from_row(row)
        updates = []
        params = []
        for field in ("name", "latitude", "longitude", "elevation_m"):
            value = defaults.get(field)
            if value is not None and getattr(station, field) != value:
                updates.append(f"{field} = ?")
                params.append(value)
                setattr(station, field, value)
        if defaults.get("meta") is not None and defaults.get("meta") != station.meta:
            updates.append("meta = ?")
            params.append(json.dumps(defaults["meta"]))
            station.meta = defaults["meta"] or {}
        if updates:
            updates.append("updated_at = ?")
            params.append(now)
            params.append(station.id)
            session.execute(
                f"UPDATE stations SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            station.updated_at = now
        return station

    params = (
        external_id,
        defaults.get("name"),
        defaults.get("latitude"),
        defaults.get("longitude"),
        defaults.get("elevation_m"),
        json.dumps(defaults.get("meta") or {}),
        now,
        now,
    )
    cursor = session.execute(
        """
        INSERT INTO stations (
            external_id, name, latitude, longitude, elevation_m, meta, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        params,
    )
    station_id = cursor.lastrowid
    return Station(
        id=station_id,
        external_id=external_id,
        name=defaults.get("name"),
        latitude=defaults.get("latitude"),
        longitude=defaults.get("longitude"),
        elevation_m=defaults.get("elevation_m"),
        meta=defaults.get("meta") or {},
        created_at=now,
        updated_at=now,
    )


def insert_observation(
    session: DatabaseSession,
    *,
    station: Station,
    payload: Dict[str, Any],
) -> bool:
    ts_utc = payload["ts_utc"]
    if not isinstance(ts_utc, str):
        ts_utc = payload["ts_utc"].astimezone(timezone.utc).isoformat()

    existing = session.fetchone(
        "SELECT id FROM observations WHERE station_id = ? AND ts_utc = ?",
        (station.id, ts_utc),
    )
    if existing:
        return False

    now = utcnow_iso()
    session.execute(
        """
        INSERT INTO observations (
            station_id,
            ts_utc,
            temperature_c,
            humidity_percent,
            pressure_hpa,
            wind_speed_ms,
            wind_direction_deg,
            rainfall_mm,
            raw_payload,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            station.id,
            ts_utc,
            payload.get("temperature_c"),
            payload.get("humidity_percent"),
            payload.get("pressure_hpa"),
            payload.get("wind_speed_ms"),
            payload.get("wind_direction_deg"),
            payload.get("rainfall_mm"),
            json.dumps(payload.get("raw_payload") or {}),
            now,
        ),
    )
    return True


def count_stations(session: DatabaseSession) -> int:
    row = session.fetchone("SELECT COUNT(*) AS cnt FROM stations")
    if isinstance(row, dict):
        return int(row["cnt"])
    return int(row[0])


def count_observations(session: DatabaseSession) -> int:
    row = session.fetchone("SELECT COUNT(*) AS cnt FROM observations")
    if isinstance(row, dict):
        return int(row["cnt"])
    return int(row[0])
