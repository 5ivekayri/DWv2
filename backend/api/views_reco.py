"""Recommendation view backed by Redis caching and OpenRouter."""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests import RequestException

try:  # pragma: no cover - Django might be unavailable in tests
    from django.http import JsonResponse  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without Django
    JsonResponse = None  # type: ignore

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 45 * 60
RATE_LIMIT_MAX_REQUESTS = 20
RATE_LIMIT_TTL_SECONDS = 60 * 60
OPENROUTER_URL = os.getenv(
    "OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions"
)
PROMPT_START_MARKER = "<!-- RECO_PROMPT_START -->"
PROMPT_END_MARKER = "<!-- RECO_PROMPT_END -->"


class SimpleResponse:
    """Fallback response object used when Django is not installed."""

    def __init__(self, data: Dict[str, Any], status: int = 200) -> None:
        self.data = data
        self.status_code = status

    @property
    def content(self) -> bytes:
        return json.dumps(self.data).encode("utf-8")


class InMemoryRedis:
    """Simple Redis-like storage for environments without a running Redis server."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def _cleanup_if_needed(self, key: str) -> None:
        entry = self._data.get(key)
        if not entry:
            return
        expires_at = entry.get("expires_at")
        if expires_at is not None and expires_at <= time.time():
            self._data.pop(key, None)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._data[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }

    def get(self, key: str) -> Optional[str]:
        self._cleanup_if_needed(key)
        entry = self._data.get(key)
        if not entry:
            return None
        return entry["value"]

    def incr(self, key: str, amount: int = 1) -> int:
        self._cleanup_if_needed(key)
        entry = self._data.get(key)
        if not entry:
            value = amount
            self._data[key] = {
                "value": str(value),
                "expires_at": None,
            }
            return value
        value = int(entry["value"]) + amount
        entry["value"] = str(value)
        return value

    def ttl(self, key: str) -> int:
        self._cleanup_if_needed(key)
        entry = self._data.get(key)
        if not entry:
            return -2
        expires_at = entry.get("expires_at")
        if expires_at is None:
            return -1
        remaining = int(expires_at - time.time())
        if remaining < 0:
            self._data.pop(key, None)
            return -2
        return remaining

    def expire(self, key: str, ttl: int) -> bool:
        self._cleanup_if_needed(key)
        entry = self._data.get(key)
        if not entry:
            return False
        entry["expires_at"] = time.time() + ttl
        return True

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def flushall(self) -> None:
        self._data.clear()


class RedisAdapter:
    """Wrapper that prefers a real Redis client but gracefully falls back to memory."""

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client or self._initialise_client()

    @staticmethod
    def _initialise_client() -> Any:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return InMemoryRedis()
        try:  # pragma: no cover - exercised only when redis is installed
            import redis  # type: ignore

            return redis.Redis.from_url(redis_url, decode_responses=True)
        except Exception:  # pragma: no cover - fallback when redis is unavailable
            logger.warning("Redis unavailable, using in-memory cache instead", exc_info=True)
            return InMemoryRedis()

    @property
    def client(self) -> Any:
        return self._client

    def _execute(self, command: str, *args: Any, **kwargs: Any) -> Any:
        try:
            method = getattr(self._client, command)
            return method(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - executes only with broken redis
            logger.warning("Redis command %s failed: %s", command, exc, exc_info=True)
            self._client = InMemoryRedis()
            method = getattr(self._client, command)
            return method(*args, **kwargs)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._execute("setex", key, ttl, value)

    def get(self, key: str) -> Optional[str]:
        return self._execute("get", key)

    def incr(self, key: str, amount: int = 1) -> int:
        return self._execute("incr", key, amount)

    def ttl(self, key: str) -> int:
        return self._execute("ttl", key)

    def expire(self, key: str, ttl: int) -> bool:
        return self._execute("expire", key, ttl)

    def delete(self, key: str) -> None:
        self._execute("delete", key)

    def flushall(self) -> None:
        if hasattr(self._client, "flushall"):
            self._execute("flushall")


_redis_adapter = RedisAdapter()


@dataclass
class RequestLike:
    """Lightweight request abstraction for tests and framework-agnostic usage."""

    GET: Dict[str, str]
    META: Dict[str, str]


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


def _make_response(payload: Dict[str, Any], status: int = 200) -> Any:
    if JsonResponse:
        return JsonResponse(payload, status=status)  # type: ignore[arg-type]
    return SimpleResponse(payload, status=status)


def _load_system_prompt() -> str:
    architecture_path = Path(__file__).resolve().parents[2] / "docs" / "ARCHITECTURE.md"
    try:
        content = architecture_path.read_text(encoding="utf-8")
        start = content.index(PROMPT_START_MARKER) + len(PROMPT_START_MARKER)
        end = content.index(PROMPT_END_MARKER, start)
        return content[start:end].strip()
    except Exception:
        logger.warning("Falling back to default LLM prompt", exc_info=True)
        return (
            "Ты — лаконичный погодный стилист. Ответь коротким советом по одежде, "
            "опираясь на координаты пользователя."
        )


_SYSTEM_PROMPT = _load_system_prompt()


def _parse_coordinate(raw_value: Optional[str], name: str) -> float:
    if raw_value is None:
        raise ValueError(f"Missing {name}")
    value = float(raw_value)
    if name == "lat" and not -90.0 <= value <= 90.0:
        raise ValueError("Latitude must be between -90 and 90")
    if name == "lon" and not -180.0 <= value <= 180.0:
        raise ValueError("Longitude must be between -180 and 180")
    return value


def _get_client_ip(request: Any) -> str:
    meta = getattr(request, "META", {}) or {}
    return meta.get("HTTP_X_FORWARDED_FOR") or meta.get("REMOTE_ADDR") or "anonymous"


def _redis_cache_key(lat: float, lon: float) -> str:
    return f"reco:{lat:.4f}:{lon:.4f}"


def _rate_limit_key(ip: str) -> str:
    return f"reco:rate:{ip}"


def _enforce_rate_limit(ip: str) -> None:
    key = _rate_limit_key(ip)
    current = _redis_adapter.incr(key)
    ttl = _redis_adapter.ttl(key)
    if ttl in (-1, -2):
        _redis_adapter.expire(key, RATE_LIMIT_TTL_SECONDS)
        ttl = RATE_LIMIT_TTL_SECONDS
    if current > RATE_LIMIT_MAX_REQUESTS:
        retry_after = ttl if ttl and ttl > 0 else RATE_LIMIT_TTL_SECONDS
        raise RateLimitExceeded(retry_after)


def _call_openrouter(lat: float, lon: float) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL")
    if not api_key or not model:
        raise RuntimeError("OpenRouter credentials are not configured")

    now = datetime.utcnow()
    is_daytime = 6 <= now.hour < 20
    user_prompt = (
        f"Координаты: lat={lat:.4f}, lon={lon:.4f}. "
        f"Сейчас {'дневное' if is_daytime else 'ночное'} время (UTC). "
        "Дай совет по одежде."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_APP_URL")
    if referer:
        headers["HTTP-Referer"] = referer
    app_name = os.getenv("OPENROUTER_APP_NAME")
    if app_name:
        headers["X-Title"] = app_name

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 128,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected OpenRouter response structure") from exc


def _season_for(lat: float, when: datetime) -> str:
    month = when.month
    is_northern = lat >= 0
    season_map = {
        (12, 1, 2): ("winter", "summer"),
        (3, 4, 5): ("spring", "autumn"),
        (6, 7, 8): ("summer", "winter"),
        (9, 10, 11): ("autumn", "spring"),
    }
    for months, seasons in season_map.items():
        if month in months:
            return seasons[0] if is_northern else seasons[1]
    return "spring"


def _fallback_recommendation(lat: float, lon: float) -> str:
    now = datetime.utcnow()
    season = _season_for(lat, now)
    is_daytime = 6 <= now.hour < 20
    base = {
        "winter": "Теплая куртка, свитер и утепленные ботинки",
        "spring": "Легкая куртка или свитер и закрытые кроссовки",
        "summer": "Легкая одежда и комфортная обувь",
        "autumn": "Ветровка и многослойность, влагостойкая обувь",
    }
    extras = (
        "Возьми зонт."
        if season in {"spring", "autumn"}
        else "Дополни образ аксессуарами по погоде."
    )
    if not is_daytime:
        extras = (
            "Добавь теплый слой и световозвращающие элементы."
            if season == "winter"
            else "Возьми легкую куртку на вечер."
        )
    return (
        f"{base.get(season, 'Одевайся по погоде')}. {extras} "
        f"(lat {lat:.2f}, lon {lon:.2f})."
    )


def recommendation_view(request: Any) -> Any:
    try:
        lat = _parse_coordinate(getattr(request, "GET", {}).get("lat"), "lat")
        lon = _parse_coordinate(getattr(request, "GET", {}).get("lon"), "lon")
    except (ValueError, TypeError) as exc:
        logger.debug("Invalid coordinates: %s", exc)
        return _make_response({"error": str(exc)}, status=400)

    ip = _get_client_ip(request)
    try:
        _enforce_rate_limit(ip)
    except RateLimitExceeded as exc:
        logger.info("Rate limit exceeded for %s", ip)
        response = _make_response({"error": "rate_limit_exceeded", "retry_after": exc.retry_after}, 429)
        if JsonResponse:
            response["Retry-After"] = str(exc.retry_after)  # type: ignore[index]
        elif isinstance(response, SimpleResponse):
            response.data["retry_after"] = exc.retry_after
        return response

    cache_key = _redis_cache_key(lat, lon)
    cached = _redis_adapter.get(cache_key)
    if cached:
        try:
            payload = json.loads(cached)
            payload["cached"] = True
            return _make_response(payload, status=200)
        except json.JSONDecodeError:  # pragma: no cover - defensive branch
            logger.warning("Failed to decode cached payload, ignoring entry", exc_info=True)
            _redis_adapter.delete(cache_key)

    try:
        recommendation = _call_openrouter(lat, lon)
        source = "openrouter"
    except (RuntimeError, RequestException) as exc:
        logger.warning("OpenRouter failed, using fallback: %s", exc)
        recommendation = _fallback_recommendation(lat, lon)
        source = "fallback"

    payload = {
        "recommendation": recommendation,
        "source": source,
        "lat": lat,
        "lon": lon,
    }

    try:
        _redis_adapter.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    except Exception:  # pragma: no cover - adapter already handles fallbacks
        logger.warning("Failed to cache recommendation", exc_info=True)

    return _make_response(payload, status=200)


def reset_redis_adapter(adapter: Optional[RedisAdapter] = None) -> None:
    """Helper for tests to swap the redis adapter instance."""
    global _redis_adapter
    _redis_adapter = adapter or RedisAdapter(InMemoryRedis())


__all__ = [
    "recommendation_view",
    "RequestLike",
    "SimpleResponse",
    "reset_redis_adapter",
    "InMemoryRedis",
    "RedisAdapter",
]
