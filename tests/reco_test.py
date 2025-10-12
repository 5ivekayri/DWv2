import json
from types import SimpleNamespace

import pytest

from backend.api import views_reco
from backend.api.views_reco import (
    CACHE_TTL_SECONDS,
    OPENROUTER_URL,
    InMemoryRedis,
    RedisAdapter,
    recommendation_view,
    reset_redis_adapter,
)
import responses


@pytest.fixture(autouse=True)
def _reset_cache():
    adapter = RedisAdapter(InMemoryRedis())
    reset_redis_adapter(adapter)
    yield
    adapter.flushall()
    reset_redis_adapter(RedisAdapter(InMemoryRedis()))


@pytest.fixture
def openrouter_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    monkeypatch.setenv("OPENROUTER_APP_NAME", "DW Test")
    yield
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_APP_NAME", raising=False)


def _extract_payload(response):
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.content.decode("utf-8"))


def _make_request(lat, lon, ip="10.0.0.1"):
    return SimpleNamespace(GET={"lat": str(lat), "lon": str(lon)}, META={"REMOTE_ADDR": ip})


def test_recommendation_cached(openrouter_env):
    request = _make_request(55.75, 37.61)

    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            OPENROUTER_URL,
            json={
                "choices": [
                    {"message": {"content": "Возьми плащ и шарф."}},
                ]
            },
            status=200,
        )
        response = recommendation_view(request)
        payload = _extract_payload(response)
        assert payload["source"] == "openrouter"
        assert "плащ" in payload["recommendation"].lower()
        assert len(rsps.calls) == 1

    cache_key = views_reco._redis_cache_key(55.75, 37.61)  # type: ignore[attr-defined]
    ttl = views_reco._redis_adapter.ttl(cache_key)
    assert CACHE_TTL_SECONDS - 5 <= ttl <= CACHE_TTL_SECONDS

    with responses.RequestsMock() as rsps:
        cached_response = recommendation_view(request)
        cached_payload = _extract_payload(cached_response)
        assert cached_payload["cached"] is True
        assert cached_payload["recommendation"] == payload["recommendation"]
        assert len(rsps.calls) == 0


def test_recommendation_fallback(openrouter_env):
    request = _make_request(40.71, -74.0)

    with responses.RequestsMock() as rsps:
        rsps.add("POST", OPENROUTER_URL, status=503, json={"error": "overload"})
        response = recommendation_view(request)

    payload = _extract_payload(response)
    assert payload["source"] == "fallback"
    assert "lat" in payload["recommendation"].lower()


def test_rate_limit_enforced(openrouter_env):
    request = _make_request(48.85, 2.35, ip="203.0.113.5")

    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            OPENROUTER_URL,
            json={"choices": [{"message": {"content": "Просто надень куртку."}}]},
            status=200,
        )
        first = recommendation_view(request)
        first_payload = _extract_payload(first)
        assert first_payload["source"] == "openrouter"

    # Subsequent calls hit the cache but should still count towards the rate limit.
    for _ in range(19):
        with responses.RequestsMock() as rsps:
            rsps.add(
                "POST",
                OPENROUTER_URL,
                json={"choices": [{"message": {"content": "Просто надень куртку."}}]},
                status=200,
            )
            response = recommendation_view(request)
            payload = _extract_payload(response)
            assert payload["recommendation"] == first_payload["recommendation"]

    over_limit = recommendation_view(request)
    over_payload = _extract_payload(over_limit)
    assert over_limit.status_code == 429
    assert over_payload["error"] == "rate_limit_exceeded"
    assert over_payload["retry_after"] >= 1
