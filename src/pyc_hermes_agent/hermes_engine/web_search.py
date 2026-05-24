"""Network web search surface (provider-neutral facade, urllib-only backends)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_DISABLE_ENV = "PYC_HERMES_DISABLE_WEB_SEARCH"
_ENV_PROVIDER = "PYC_HERMES_WEB_SEARCH_PROVIDER"

ALLOWED_WEB_SEARCH_PROVIDERS = frozenset({"duckduckgo", "wikipedia", "chain"})


def duckduckgo_instant_answer_json(query: str, *, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Fetch DuckDuckGo Instant Answer API JSON (`format=json`)."""
    params = {"q": query.strip(), "format": "json", "no_html": "1", "no_redirect": "1"}
    url = "https://api.duckduckgo.com/?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "PycHermesAgent/1.0 (web_search;duckduckgo)"})

    opener_fn = opener or urlopen

    with opener_fn(req, timeout=12) as resp:  # type: ignore[misc]
        raw = resp.read().decode("utf-8")

    return json.loads(raw)


def wikipedia_opensearch_json(query: str, *, opener: Callable[..., Any] | None = None) -> Any:
    """GET MediaWiki ``opensearch`` JSON (titles, summaries, urls)."""

    params = {"action": "opensearch", "search": query.strip(), "limit": 15, "namespace": "0", "format": "json"}
    url = "https://en.wikipedia.org/w/api.php?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "PycHermesAgent/1.0 (web_search;wikipedia)"})

    opener_fn = opener or urlopen
    with opener_fn(req, timeout=12) as resp:  # type: ignore[misc]
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _normalize_provider(name: str | None) -> str:
    fallback = "duckduckgo"
    if not name or not isinstance(name, str):
        raw = os.environ.get(_ENV_PROVIDER, fallback).strip().lower()
    else:
        raw = name.strip().lower()
        if raw not in ALLOWED_WEB_SEARCH_PROVIDERS:
            return fallback
        return raw or fallback
    if raw not in ALLOWED_WEB_SEARCH_PROVIDERS:
        return fallback
    return raw or fallback


def _payload_from_arrays(
    query: str,
    *,
    provider: str,
    titles: list[str],
    summaries: list[str],
    urls: list[str],
    max_results: int,
) -> dict[str, Any]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    for title, summary, uri in zip(titles, summaries, urls, strict=False):
        t = title.strip()
        s = summary.strip()
        u = uri.strip()
        if not u and not s:
            continue
        key = u or (t + "|" + s[:80])
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            {
                "title": t or u or "untitled",
                "snippet": s or t[:500],
                "source_uri": u,
                "source_type": "web",
                "provider": provider,
                "timestamp": None,
            }
        )

    capped_max = max(1, max_results)
    capped = merged[:capped_max]
    citations = [
        {"title": r["title"], "snippet": r["snippet"], "source_uri": r["source_uri"], "source_type": "web", "provider": provider}
        for r in capped
    ]
    warnings: list[str] = []
    if not citations:
        warnings.append("no_results")
    return {
        "query": query.strip(),
        "provider": provider,
        "requested_at_unix": time.time(),
        "ok": True,
        "results": capped,
        "citations": citations,
        "warnings": warnings,
    }


def _parse_ddg_to_results(
    data: Mapping[str, Any],
    *,
    provider: str,
    max_results: int,
    seen: set[str],
    collector: list[dict[str, Any]],
) -> None:

    def add_item(title: str, snippet: str, source_uri: str) -> None:
        uri = (source_uri or "").strip()
        snippet_stripped = snippet.strip()
        if not uri and not snippet_stripped:
            return
        key = uri or snippet_stripped[:120]
        if key in seen:
            return
        seen.add(key)
        collector.append(
            {
                "title": title.strip() or uri or "untitled",
                "snippet": snippet_stripped,
                "source_uri": uri,
                "source_type": "web",
                "provider": provider,
                "timestamp": None,
            }
        )

    abstract = str(data.get("Abstract") or "").strip()
    abstract_text = abstract or str(data.get("Answer") or "").strip()
    abstract_url = str(data.get("AbstractURL") or "").strip()

    heading = str(data.get("Heading") or "").strip()

    if abstract_text and abstract_url:
        add_item(heading or abstract_url, abstract_text, abstract_url)
    elif abstract_text:
        add_item(heading or "instant_answer", abstract_text, abstract_url)

    for topic in _flatten_related_topics(data.get("RelatedTopics") or []):
        title = str(topic.get("Text") or topic.get("Name") or "").strip()
        first_url = str(topic.get("FirstURL") or "").strip()
        snippet = title.split(" - ", 1)[-1][:500] if title else ""
        if title or first_url:
            add_item(title or first_url, snippet, first_url)

    definitions = data.get("Definitions")
    if isinstance(definitions, list):
        for row in definitions:
            if not isinstance(row, Mapping):
                continue
            txt = str(row.get("Text") or "").strip()
            src = str(row.get("DefinitionURL") or row.get("URL") or "").strip()
            tit = str(row.get("Heading") or row.get("Name") or "definition").strip()
            add_item(tit, txt, src)

    if not collector and heading:
        add_item(heading, abstract_text, abstract_url)

    capped_max = max(1, max_results)
    collector[:] = collector[:capped_max]


def web_search_duckduckgo(
    query: str,
    *,
    max_results: int = 8,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    q = query.strip()
    collector: list[dict[str, Any]] = []

    seen: set[str] = set()
    provider = "duckduckgo"

    try:
        data = duckduckgo_instant_answer_json(q, opener=opener)
    except (TimeoutError, OSError, URLError, json.JSONDecodeError, ValueError) as exc:
        return _empty_payload(q, error=type(exc).__name__, provider_hint=provider)

    _parse_ddg_to_results(data, provider=provider, max_results=max_results, seen=seen, collector=collector)
    citations = [
        {"title": r["title"], "snippet": r["snippet"], "source_uri": r["source_uri"], "source_type": "web", "provider": provider}
        for r in collector
    ]
    warnings: list[str] = []
    if not citations:
        warnings.append("no_results")
    return {
        "query": q,
        "provider": provider,
        "requested_at_unix": time.time(),
        "ok": True,
        "results": collector,
        "citations": citations,
        "warnings": warnings,
    }


def web_search_wikipedia(
    query: str,
    *,
    max_results: int = 8,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    q = query.strip()
    provider = "wikipedia"
    try:
        raw = wikipedia_opensearch_json(q, opener=opener)
    except (TimeoutError, OSError, URLError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return _empty_payload(q, error=type(exc).__name__, provider_hint=provider)

    if not isinstance(raw, list) or len(raw) < 4 or not isinstance(raw[1], list):
        payload = _payload_from_arrays(q, provider=provider, titles=[], summaries=[], urls=[], max_results=max_results)
        payload["warnings"] = [*payload["warnings"], "malformed_payload"]
        return payload

    titles = [str(t) for t in raw[1]]
    summaries = [str(s) for s in raw[2]] if isinstance(raw[2], list) else []
    urls = [str(u) for u in raw[3]] if isinstance(raw[3], list) else []
    summaries += [""] * max(0, len(titles) - len(summaries))
    urls += [""] * max(0, len(titles) - len(urls))
    return _payload_from_arrays(q, provider=provider, titles=titles, summaries=summaries, urls=urls, max_results=max_results)


def web_search_normalized(
    query: str,
    *,
    max_results: int = 8,
    opener: Callable[..., Any] | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """
    Normalize search into ``results`` + ``citations`` (desktop-compatible).

    Pick ``duckduckgo``, ``wikipedia``, or ``chain`` via optional ``provider`` argument
    or ``PYC_HERMES_WEB_SEARCH_PROVIDER`` env (chain tries DuckDuckGo, then Wikipedia when empty).
    """
    q = query.strip()
    if os.environ.get(_DISABLE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return _empty_payload(q, disabled=True, provider_hint=_normalize_provider(provider))

    if not q:
        return _empty_payload(q, error="EMPTY_QUERY", provider_hint=_normalize_provider(provider))

    selected = _normalize_provider(provider)

    if selected == "duckduckgo":
        return web_search_duckduckgo(q, max_results=max_results, opener=opener)
    if selected == "wikipedia":
        return web_search_wikipedia(q, max_results=max_results, opener=opener)

    # chain → prefer DuckDuckGo; if empty, fall back to Wikipedia.
    ddg = web_search_duckduckgo(q, max_results=max_results, opener=opener)
    if ddg["citations"]:
        fused = dict(ddg)
        fused["provider"] = "chain"
        fused["meta"] = {"sources_tried": ["duckduckgo"]}
        return fused

    wiki = web_search_wikipedia(q, max_results=max_results, opener=opener)
    fused_w = dict(wiki)
    fused_w["provider"] = "chain"
    fused_w["meta"] = {"sources_tried": ["duckduckgo", "wikipedia"]}
    return fused_w


def run_web_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "") or "").strip()
    raw_max = arguments.get("max_results", 8)

    raw_provider = arguments.get("provider", None)
    resolved_provider = None if raw_provider in (None, "") else str(raw_provider)

    try:
        max_results = int(raw_max) if raw_max is not None else 8
    except (TypeError, ValueError):
        max_results = 8

    capped_max = max(1, min(max_results, 20))
    return web_search_normalized(query, max_results=capped_max, provider=resolved_provider)


def _empty_payload(
    query: str,
    *,
    error: str | None = None,
    disabled: bool = False,
    provider_hint: str = "duckduckgo",
) -> dict[str, Any]:
    warnings: list[str] = []

    meta: dict[str, Any] = {"disabled": disabled, "error": error}
    ok = not disabled and error is None

    if disabled:
        warnings.append(_DISABLE_ENV)

    elif error == "EMPTY_QUERY":
        warnings.append("empty_query")
    elif error:
        warnings.append(f"request_failed:{error}")

    return {
        "query": query.strip(),
        "provider": provider_hint,
        "requested_at_unix": time.time(),
        "ok": ok,
        "results": [],
        "citations": [],
        "warnings": warnings,
        "meta": meta,
    }


def _flatten_related_topics(nodes: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            nested = item.get("Topics")
            if isinstance(nested, list):
                for child in nested:
                    walk(child)

                return

            if item.get("FirstURL") or item.get("Text"):
                out.append(item)

        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(nodes)

    return out


__all__ = [
    "ALLOWED_WEB_SEARCH_PROVIDERS",
    "duckduckgo_instant_answer_json",
    "run_web_search_tool",
    "web_search_duckduckgo",
    "web_search_normalized",
    "web_search_wikipedia",
    "wikipedia_opensearch_json",
]
