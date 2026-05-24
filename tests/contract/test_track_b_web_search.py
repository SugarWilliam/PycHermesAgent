"""Contract tests for Track B web_search cache, quota (mocked outbound)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pyc_hermes_agent.hermes_engine.web_search as web_search_mod
from pyc_hermes_agent.hermes_engine.web_search_runtime import reset_web_search_runtime_state_for_tests


@pytest.fixture(autouse=True)
def _fresh_web_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_web_search_runtime_state_for_tests()

    monkeypatch.setenv("PYC_HERMES_WEB_SEARCH_DISABLE_CACHE", "1")

    monkeypatch.setenv("PYC_HERMES_WEB_SEARCH_QUOTA_PER_MINUTE", "9000")
    monkeypatch.setenv("PYC_HERMES_WEB_SEARCH_QUOTA_PER_HOUR", "900000")


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self._raw = json.dumps(body, ensure_ascii=True).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


def _stub_payload() -> dict:

    return {
        "Abstract": "Smoke abstract.",
        "AbstractURL": "https://example.com/a",
        "Heading": "Topic",
        "RelatedTopics": [],
    }


def test_web_search_disk_cache_returns_hit_without_second_network_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.delenv("PYC_HERMES_WEB_SEARCH_DISABLE_CACHE", raising=False)

    monkeypatch.setenv("PYC_HERMES_WEB_SEARCH_CACHE_TTL_SEC", "60")

    calls = {"count": 0}

    def _open(req: object, **_k: object) -> _FakeResponse:
        calls["count"] += 1

        return _FakeResponse(_stub_payload())

    monkeypatch.setattr(web_search_mod, "urlopen", _open)

    first = web_search_mod.web_search_normalized("cache-hit-query", workspace_root=tmp_path, provider="duckduckgo")

    second = web_search_mod.web_search_normalized("cache-hit-query", workspace_root=tmp_path, provider="duckduckgo")

    assert first["meta"].get("cache_hit") is False
    assert second["meta"].get("cache_hit") is True

    assert second["meta"].get("latency_ms") == 0
    assert calls["count"] == 1


def test_web_search_quota_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYC_HERMES_WEB_SEARCH_DISABLE_CACHE", "1")

    monkeypatch.setenv("PYC_HERMES_WEB_SEARCH_QUOTA_PER_MINUTE", "1")

    calls = {"count": 0}

    def _open(req: object, **_k: object) -> _FakeResponse:
        calls["count"] += 1

        return _FakeResponse(_stub_payload())

    monkeypatch.setattr(web_search_mod, "urlopen", _open)

    first = web_search_mod.web_search_normalized("alpha", provider="duckduckgo")

    assert first["ok"] is True
    assert calls["count"] == 1

    second = web_search_mod.web_search_normalized("beta", provider="duckduckgo")

    assert second["ok"] is False

    assert second["meta"].get("error") == "QUOTA_EXCEEDED"
    assert calls["count"] == 1

