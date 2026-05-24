"""Contract tests for web_search (mocked urllib — no outbound network assumed)."""

from __future__ import annotations

import json

import pytest

from pyc_hermes_agent.contracts import ToolCall
from pyc_hermes_agent.hermes_engine import create_meta_harness_tool_registry
import pyc_hermes_agent.hermes_engine.web_search as web_search_mod
from pyc_hermes_agent.hermes_engine.web_search import run_web_search_tool, web_search_normalized


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self._raw = json.dumps(body, ensure_ascii=True).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


class _FakeBytesResp:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> _FakeBytesResp:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _fake_payload() -> dict:
    return {
        "Abstract": "Forecast evidence snippet.",
        "AbstractURL": "https://example.com/page",
        "Heading": "Example Topic",
        "RelatedTopics": [{"Text": "Second hit - trailing text", "FirstURL": "https://example.com/b"}],
    }


def test_web_search_normalized_maps_instant_answer_to_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web_search_mod, "urlopen", lambda *_a, **_k: _FakeResponse(_fake_payload()))

    result = web_search_normalized("forecast evidence")

    assert result["ok"] is True

    cites = result["citations"]
    assert len(cites) >= 1
    assert cites[0]["source_type"] == "web"
    assert cites[0]["source_uri"] == "https://example.com/page"
    assert cites[0]["provider"] == "duckduckgo"


def test_web_search_respects_disable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYC_HERMES_DISABLE_WEB_SEARCH", "1")
    monkeypatch.setattr(web_search_mod, "urlopen", lambda *_a, **_k: _FakeResponse(_fake_payload()))

    out = web_search_normalized("anything")
    assert out["ok"] is False
    assert out["citations"] == []
    meta = out.get("meta")
    assert isinstance(meta, dict) and meta.get("disabled")


def test_run_web_search_tool_empty_query() -> None:
    out = run_web_search_tool({"query": "  "})
    assert out["ok"] is False
    assert "empty_query" in out["warnings"]


def test_tool_registry_dispatches_web_search(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = create_meta_harness_tool_registry()
    assert registry.has_tool("web_search") is True

    monkeypatch.setattr(web_search_mod, "urlopen", lambda *_a, **_k: _FakeResponse(_fake_payload()))

    res = registry.dispatch(
        ToolCall(
            id="t1",
            name="web_search",
            arguments=json.dumps({"query": "anything", "max_results": 3}, ensure_ascii=True),
        )
    )

    assert res.is_error is False
    assert res.structured_content is not None
    cites = res.structured_content.get("citations") or []
    assert isinstance(cites, list) and len(cites) >= 1
    assert cites[0].get("source_type") == "web"


def test_meta_harness_registry_includes_formal_and_web() -> None:
    registry = create_meta_harness_tool_registry()
    names = {d.name for d in registry.list_descriptors()}
    assert names == {"formal_analysis", "knowledge_retrieve", "web_search"}


def test_web_search_wikipedia_provider_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    wiki = json.dumps(["q", ["Title A"], ["Summary line"], ["https://en.wikipedia.org/wiki/A"]]).encode()

    def _open(req: object, **_k: object) -> _FakeBytesResp:
        url = getattr(req, "full_url", None) or getattr(req, "get_full_url", lambda: "")()
        assert "wikipedia.org" in url
        return _FakeBytesResp(wiki)

    monkeypatch.setattr(web_search_mod, "urlopen", _open)

    out = web_search_normalized("anything", provider="wikipedia")
    assert out["ok"] is True
    assert out["provider"] == "wikipedia"
    assert out["citations"] and out["citations"][0]["source_uri"].endswith("/wiki/A")


def test_web_search_chain_uses_wikipedia_when_ddg_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    wiki = json.dumps(["q", ["T"], ["s"], ["https://en.wikipedia.org/wiki/Topic"]]).encode()
    dq = [_FakeResponse({}), _FakeBytesResp(wiki)]

    def _open(req: object, **_k: object):
        url = getattr(req, "full_url", None) or getattr(req, "get_full_url", lambda: "")()
        if "duckduckgo.com" in url:
            return dq[0]
        if "wikipedia.org" in url:
            return dq[1]
        raise AssertionError(url)

    monkeypatch.setattr(web_search_mod, "urlopen", _open)

    out = web_search_normalized("alpha", provider="chain")
    assert out["provider"] == "chain"
    assert any("wikipedia" in (c.get("provider") or "") for c in out["citations"])
    assert isinstance(out.get("meta"), dict)

