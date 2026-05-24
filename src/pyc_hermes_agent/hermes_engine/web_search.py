"""Network web search surface (provider-neutral facade, urllib-only backends)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pyc_hermes_agent.hermes_engine import web_search_runtime as ws_rt

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


def _wrap_timed(payload: dict[str, Any], t0: float, **extra_meta: Any) -> dict[str, Any]:
    latency_ms = max(0, int((time.perf_counter() - t0) * 1000))
    merged_extra = {"latency_ms": latency_ms, **extra_meta}
    if isinstance(payload.get("meta"), dict):
        meta = dict(payload["meta"])
        meta.update(merged_extra)
        out = dict(payload)
        out["meta"] = meta
        return out
    return ws_rt.merge_meta(payload, merged_extra)


def _duckduckgo_tracked(query: str, *, max_results: int, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    backoff = ws_rt.provider_backoff_until("duckduckgo")
    if backoff:
        base = _empty_payload(query, error="BACKOFF", provider_hint="duckduckgo")
        return ws_rt.merge_meta(
            base,
            {"backoff_until_unix": backoff, "circuit_provider": "duckduckgo"},
        )

    raw = web_search_duckduckgo(query, max_results=max_results, opener=opener)
    if raw.get("ok"):
        ws_rt.note_provider_success("duckduckgo")
        return dict(raw)

    ws_rt.note_provider_failure("duckduckgo")
    return dict(raw)


def _wikipedia_tracked(query: str, *, max_results: int, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    backoff = ws_rt.provider_backoff_until("wikipedia")
    if backoff:
        base = _empty_payload(query, error="BACKOFF", provider_hint="wikipedia")
        return ws_rt.merge_meta(
            base,
            {"backoff_until_unix": backoff, "circuit_provider": "wikipedia"},
        )

    raw = web_search_wikipedia(query, max_results=max_results, opener=opener)
    if raw.get("ok"):
        ws_rt.note_provider_success("wikipedia")
        return dict(raw)

    ws_rt.note_provider_failure("wikipedia")
    return dict(raw)


def web_search_normalized(
    query: str,
    *,
    max_results: int = 8,
    opener: Callable[..., Any] | None = None,
    provider: str | None = None,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """
    Normalize search into ``results`` + ``citations`` (desktop-compatible).

    Pick ``duckduckgo``, ``wikipedia``, or ``chain`` via optional ``provider`` argument
    or ``PYC_HERMES_WEB_SEARCH_PROVIDER`` env (chain tries DuckDuckGo, then Wikipedia when empty).

    Optional ``workspace_root`` chooses the packaging cache subdirectory under writable ``cache/web_search``.
    """
    ws_path = Path(workspace_root).expanduser() if workspace_root else None
    cache_dir = ws_rt.resolve_web_search_cache_dir(ws_path)

    q = query.strip()
    hint = _normalize_provider(provider)

    base_meta_skeleton: dict[str, Any] = {"cache_hit": False, "cache_dir": str(cache_dir)}

    if os.environ.get(_DISABLE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        out = _empty_payload(q, disabled=True, provider_hint=hint)
        return ws_rt.merge_meta(out, base_meta_skeleton)

    if not q:
        out = _empty_payload(q, error="EMPTY_QUERY", provider_hint=hint)
        return ws_rt.merge_meta(out, base_meta_skeleton)

    selected = _normalize_provider(provider)
    cache_key_provider = selected
    cache_fp = ws_rt.cache_file_path(cache_dir, provider=cache_key_provider, query=q, max_results=max_results)
    cached = ws_rt.read_disk_cache(cache_fp)
    if cached is not None:
        merged = ws_rt.merge_meta(cached, {**base_meta_skeleton, "cache_hit": True, "latency_ms": 0})
        return merged

    ok_reserve, quota_meta = ws_rt.try_consume_network_quota_slot()
    if not ok_reserve:
        base = _empty_payload(q, error="QUOTA_EXCEEDED", provider_hint=selected)
        return ws_rt.merge_meta(base, {**base_meta_skeleton, **quota_meta})

    t0 = time.perf_counter()

    if selected == "duckduckgo":
        raw = _duckduckgo_tracked(q, max_results=max_results, opener=opener)
        out = _wrap_timed(raw, t0, **quota_meta)
    elif selected == "wikipedia":
        raw = _wikipedia_tracked(q, max_results=max_results, opener=opener)
        out = _wrap_timed(raw, t0, **quota_meta)
    else:
        sources_tried: list[str] = []
        backoff_meta: dict[str, Any] = {}

        ddg = _duckduckgo_tracked(q, max_results=max_results, opener=opener)
        if isinstance(ddg.get("meta"), dict) and ddg["meta"].get("circuit_provider"):
            backoff_meta.setdefault("skipped_for_backoff", []).append("duckduckgo")

        if ddg.get("citations"):
            fused = dict(ddg)
            fused["provider"] = "chain"
            fused.setdefault("meta", {})
            fused["meta"] = {**dict(fused["meta"]), "sources_tried": ["duckduckgo"]}
            out = _wrap_timed(fused, t0, **quota_meta, **backoff_meta)
        else:
            sources_tried.append("duckduckgo")

            wiki = _wikipedia_tracked(q, max_results=max_results, opener=opener)
            if isinstance(wiki.get("meta"), dict) and wiki["meta"].get("circuit_provider"):
                backoff_meta.setdefault("skipped_for_backoff", []).append("wikipedia")

            fused_w = dict(wiki)
            fused_w["provider"] = "chain"
            fused_w.setdefault("meta", {})
            fused_w["meta"] = {**dict(fused_w["meta"]), "sources_tried": [*sources_tried, "wikipedia"]}
            extra_chain = dict(quota_meta)
            extra_chain.update(backoff_meta)
            if backoff_meta.get("skipped_for_backoff"):
                fused_w.setdefault("warnings", [])
                if isinstance(fused_w["warnings"], list):
                    fused_w["warnings"].append("provider_skipped_for_backoff")
            out = _wrap_timed(fused_w, t0, **extra_chain)

    out = ws_rt.merge_meta(out, base_meta_skeleton)
    meta_block = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    cache_hit_false = isinstance(meta_block, dict) and meta_block.get("cache_hit") is False
    if out.get("ok") and out.get("citations") and cache_hit_false:
        ws_rt.write_disk_cache(cache_fp, out)
    return out


def run_web_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "") or "").strip()
    raw_max = arguments.get("max_results", 8)

    raw_provider = arguments.get("provider", None)
    resolved_provider = None if raw_provider in (None, "") else str(raw_provider)

    raw_ws = arguments.get("workspace_root", None)
    workspace_root = Path(str(raw_ws)).expanduser() if raw_ws else None

    try:
        max_results = int(raw_max) if raw_max is not None else 8
    except (TypeError, ValueError):
        max_results = 8

    capped_max = max(1, min(max_results, 20))
    return web_search_normalized(query, max_results=capped_max, provider=resolved_provider, workspace_root=workspace_root)


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
