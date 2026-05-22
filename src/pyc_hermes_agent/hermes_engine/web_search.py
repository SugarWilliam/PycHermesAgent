"""Minimal network web search surface (provider-neutral, urllib-only)."""

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
_DEFAULT_PROVIDER = "duckduckgo"


def duckduckgo_instant_answer_json(query: str, *, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Fetch DuckDuckGo Instant Answer API JSON (`format=json`)."""
    params = {"q": query.strip(), "format": "json", "no_html": "1", "no_redirect": "1"}
    url = "https://api.duckduckgo.com/?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "PycHermesAgent/1.0 (web_search)"})

    opener_fn = opener or urlopen

    with opener_fn(req, timeout=12) as resp:  # type: ignore[misc]
        raw = resp.read().decode("utf-8")

    return json.loads(raw)


def web_search_normalized(
    query: str,
    *,
    max_results: int = 8,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """
    Run a shallow web lookup and normalize into ``results`` + ``citations`` (desktop-compatible).

    On failure/offline/disable, returns an empty-result payload (no raise).

    Successful HTTP parses set ``ok: true`` even when snippets are empty; ``warnings``
    carries ``no_results`` in that case.
    """
    q = query.strip()
    if os.environ.get(_DISABLE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return _empty_payload(q, disabled=True)

    if not q:
        return _empty_payload(q, error="EMPTY_QUERY")

    try:
        data = duckduckgo_instant_answer_json(q, opener=opener)
    except (TimeoutError, OSError, URLError, json.JSONDecodeError, ValueError) as exc:
        return _empty_payload(q, error=type(exc).__name__)

    results: list[dict[str, Any]] = []

    seen: set[str] = set()

    def add_item(title: str, snippet: str, source_uri: str) -> None:
        uri = (source_uri or "").strip()
        snippet_stripped = snippet.strip()
        if not uri and not snippet_stripped:
            return
        key = uri or snippet_stripped[:120]
        if key in seen:
            return
        seen.add(key)
        results.append(
            {
                "title": title.strip() or uri or "untitled",
                "snippet": snippet_stripped,
                "source_uri": uri,
                "source_type": "web",
                "provider": _DEFAULT_PROVIDER,
                "timestamp": None,
            },
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

    if not results and heading:
        add_item(heading, abstract_text, abstract_url)

    capped_max = max(1, max_results)
    capped = results[:capped_max]

    citations = [
        {
            "title": r["title"],
            "snippet": r["snippet"],
            "source_uri": r["source_uri"],
            "source_type": "web",
            "provider": _DEFAULT_PROVIDER,
        }
        for r in capped
    ]

    warnings: list[str] = []

    if not citations:
        warnings.append("no_results")

    return {
        "query": q,
        "provider": _DEFAULT_PROVIDER,
        "requested_at_unix": time.time(),
        "ok": True,
        "results": capped,
        "citations": citations,
        "warnings": warnings,
    }


def run_web_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "") or "").strip()
    raw_max = arguments.get("max_results", 8)
    try:
        max_results = int(raw_max) if raw_max is not None else 8
    except (TypeError, ValueError):
        max_results = 8

    capped_max = max(1, min(max_results, 20))
    return web_search_normalized(query, max_results=capped_max)


def _empty_payload(query: str, *, error: str | None = None, disabled: bool = False) -> dict[str, Any]:
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
        "provider": _DEFAULT_PROVIDER,
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
    "duckduckgo_instant_answer_json",
    "run_web_search_tool",
    "web_search_normalized",
]
