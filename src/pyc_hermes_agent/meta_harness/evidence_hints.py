"""Lightweight multi-source summaries for grounded formal analysis (non-prover).

Produces inspectable hints for **web** grounding (HTTP URIs), **KB / MRAG** citations, and coarse
cross-lane overlaps — without asserting causal claims.

Structured Phase 3F1 validation payloads (normalized items / conflicts / edges / logic temporal hints)
live in ``meta_harness/evidence_chain.py`` and are merged under ``analysis_card.evidence_chain.validation``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse


def _host_from_uri(uri: str) -> str:
    uri = uri.strip()
    if not uri:
        return ""

    parsed = urlparse(uri)
    return (parsed.hostname or "").lower()


def summarize_network_evidence_chain(
    *,
    network_refs: list[str],
    citation_entries_total: int,
    unique_network_uris: int,
    aggregated_uri_rows_before_dedupe: int = 0,
) -> dict[str, object]:
    """Return a JSON-serializable bundle for attaching to formal ``analysis_card`` payloads.

    This does not rewrite MetaFramework conclusions; callers may merge hints into downstream UX.
    """
    refs = [str(r).strip() for r in network_refs if str(r).strip()]
    hints: list[str] = []

    if not refs:
        hints.append("no_network_ref_uris")
    hosts = {_host_from_uri(r) for r in refs if _host_from_uri(r)}
    if citation_entries_total == 0 and not refs:
        hints.append("no_network_citations")
    if aggregated_uri_rows_before_dedupe > unique_network_uris:
        hints.append("network_uri_rows_deduplicated")
    if unique_network_uris >= 2 and len(hosts) == 1:
        hints.append("network_evidence_single_host_only")
    if unique_network_uris >= 3 and len(hosts) <= 2:
        hints.append("low_network_origin_diversity")

    return {
        "hints": hints,
        "unique_uri_count": unique_network_uris,
        "citation_entry_count": citation_entries_total,
        "distinct_host_count": len(hosts),
        "hosts": sorted(hosts),
    }


def summarize_formal_multi_source_evidence_chain(
    *,
    http_refs: Sequence[str],
    web_stats: Mapping[str, Any],
    kb_stats: Mapping[str, Any],
    overlapping_http_across_kb_and_web: Sequence[str],
) -> dict[str, object]:
    """Summarize citations coming from HTTP tools versus local MRAG-shaped tool payloads."""

    http_list = [str(r).strip() for r in http_refs if str(r).strip()]
    overlap = tuple(dict.fromkeys(str(u).strip() for u in overlapping_http_across_kb_and_web if str(u).strip()))

    web_entries = int(web_stats.get("citation_entry_count") or 0)
    kb_entries = int(kb_stats.get("citation_entry_count") or 0)

    kb_block = {
        "citation_entry_count": kb_entries,
        "distinct_documents": int(kb_stats.get("distinct_documents") or 0),
        "citations_missing_ref": int(kb_stats.get("citations_missing_ref") or 0),
    }

    if kb_entries == 0 and web_entries == 0:
        return {
            "hints": ["no_tool_grounding_citations"],
            "web": {
                "hints": [],
                "unique_uri_count": 0,
                "citation_entry_count": 0,
                "distinct_host_count": 0,
                "hosts": [],
            },
            "kb": kb_block,
            "overlap_http_uris": list(overlap),
        }

    web_chain = summarize_network_evidence_chain(
        network_refs=list(http_list),
        citation_entries_total=web_entries,
        unique_network_uris=int(web_stats.get("unique_network_uris") or 0),
        aggregated_uri_rows_before_dedupe=int(web_stats.get("aggregated_uri_rows_before_dedupe") or 0),
    )

    hints: list[str] = []

    if overlap and kb_entries > 0 and web_entries > 0:
        hints.append("http_uri_overlap_across_kb_and_web")

    if kb_entries > 0 and web_entries > 0:
        hints.append("multi_source_web_and_kb_grounding")
    elif kb_entries > 0 and web_entries == 0 and not http_list:
        hints.append("local_kb_refs_only_no_http_tool_refs")
    elif web_entries > 0 and kb_entries == 0:
        hints.append("network_tool_refs_only_no_kb_citations")

    web_hints_raw = list(web_chain.get("hints") or [])
    noise_when_kb = frozenset({"no_network_ref_uris", "no_network_citations"})
    if kb_entries > 0:
        web_hints_raw = [h for h in web_hints_raw if h not in noise_when_kb]

    hints.extend(web_hints_raw)

    return {
        "hints": hints,
        "web": web_chain,
        "kb": kb_block,
        "overlap_http_uris": list(overlap),
    }
