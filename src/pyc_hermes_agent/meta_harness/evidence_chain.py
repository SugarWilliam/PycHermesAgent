"""Phase 3F1 evidence-chain validation payloads for formal grounding (structured, non-fusing).

Builds normalized evidence rows, bounded conflict hints, directional **non-causal** chain edges,
and logic/temporal escalation signals merged into ``analysis_card.evidence_chain.validation``.

This deliberately **does not** rewrite ``MetaAnalysisResult`` or bypass ``MetaFramework.execute()``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any
from urllib.parse import urlparse

from pyc_hermes_agent.contracts import MetaAnalysisResult
from pyc_hermes_agent.meta_harness import consistency
from pyc_hermes_agent.meta_harness.source_policy import (
    degraded_formal_signals,
    grounding_mix_hints,
)

_SCHEMA = "phase3f1/evidence-validation/v1"
_MAX_ITEMS = 40
_MAX_CONFLICTS = 16


def _excerpt_from_cite(cite: Mapping[str, Any]) -> str:
    for key in ("snippet", "excerpt", "text", "content", "summary"):
        blob = cite.get(key)
        if isinstance(blob, str) and blob.strip():
            return blob.strip()
    title = cite.get("title")
    return str(title).strip() if isinstance(title, str) else ""


def _canonical_http_anchor(uri: str) -> str:
    u = str(uri).strip()
    low = u.rstrip("/")
    return low


def _primary_anchor(_kind: str, cite: Mapping[str, Any]) -> str:
    uri = str(cite.get("source_uri") or "").strip()
    if uri:
        return _canonical_http_anchor(uri)
    doc = str(cite.get("document_id") or "").strip()
    chk = str(cite.get("chunk_id") or "").strip()
    if doc and chk:
        return f"pyc-hermes:mrag/{doc}/{chk}"
    if doc:
        return f"pyc-hermes:mrag/{doc}"
    # chunk-only / metadata-only anchors (avoid hashing nested dict payloads).
    bucket = chk or str(cite.get("source_type") or "kb_unknown")
    key_bits = f"{chk}|{str(cite.get('source_type') or '')}|{str(cite.get('document_id') or '')}"
    h = hashlib.sha256(key_bits.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"pyc-hermes:inline/{bucket}-{h}"


def _relevance_optional(cite: Mapping[str, Any]) -> float | None:
    raw = cite.get("relevance")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _confidence_role(excerpt: str, cite: Mapping[str, Any]) -> str:
    rel = _relevance_optional(cite)
    if len(excerpt) < 48:
        return "thin_anchor_excerpt_short"
    if rel is not None and rel <= 0.15:
        return "thin_anchor_relevance_low_numeric"
    if not excerpt.strip():
        return "thin_anchor_missing_excerpt"
    return "anchored_quote_baseline"


def normalize_evidence_items(
    *,
    web_citations: Sequence[Mapping[str, Any]],
    kb_citations: Sequence[Mapping[str, Any]],
    max_items: int = _MAX_ITEMS,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for cite in kb_citations or []:
        if not isinstance(cite, Mapping):
            continue
        excerpt = _excerpt_from_cite(cite)
        anchor = _primary_anchor("kb", cite)
        items.append(
            {
                "source_kind": "kb",
                "anchor": anchor,
                "document_id": str(cite.get("document_id") or "").strip() or None,
                "chunk_id": str(cite.get("chunk_id") or "").strip() or None,
                "source_uri": str(cite.get("source_uri") or "").strip() or None,
                "title": str(cite.get("title") or "").strip() or None,
                "excerpt": excerpt[:2000],
                "excerpt_len": len(excerpt),
                "relevance": _relevance_optional(dict(cite)),
                "confidence_role": _confidence_role(excerpt, dict(cite)),
            }
        )
        if len(items) >= max_items:
            return items[:max_items]

    for cite in web_citations or []:
        if not isinstance(cite, Mapping):
            continue
        excerpt = _excerpt_from_cite(cite)
        anchor = _primary_anchor("web", cite)
        items.append(
            {
                "source_kind": "web",
                "anchor": anchor,
                "document_id": None,
                "chunk_id": None,
                "source_uri": str(cite.get("source_uri") or "").strip() or None,
                "title": str(cite.get("title") or "").strip() or None,
                "excerpt": excerpt[:2000],
                "excerpt_len": len(excerpt),
                "relevance": _relevance_optional(dict(cite)),
                "confidence_role": _confidence_role(excerpt, dict(cite)),
            }
        )
        if len(items) >= max_items:
            break

    return items[:max_items]


def _snippet_divergence_conflict(kind: str, left: Mapping[str, Any], right: Mapping[str, Any], *, note: str, verify: str) -> dict[str, Any]:
    def side(item: Mapping[str, Any]) -> dict[str, str | None]:
        return {
            "source_kind": str(item.get("source_kind")),
            "anchor": str(item.get("anchor")),
            "title": item.get("title") if isinstance(item.get("title"), str) else None,
            "excerpt_prefix": (str(item.get("excerpt") or "")[:240] or None),
        }

    return {
        "kind": kind,
        "sources": [side(left), side(right)],
        "resolution_status": "unresolved",
        "risk_note": note,
        "verification_suggestion": verify,
    }


def derive_conflicts(
    *,
    items: Sequence[Mapping[str, Any]],
    overlapping_http_across_kb_and_web: Sequence[str],
    min_excerpt_chars: int = 24,
    jaccard_divergence_max: float = 0.18,
) -> list[dict[str, Any]]:
    """Surface **structured** disagreement hints without asserting winner/loser verdicts."""

    conflicts: list[dict[str, Any]] = []
    buckets: dict[str, list[dict[str, Any]]] = {}

    for item in items:
        if str(item.get("source_kind")) != "web":
            continue
        anc = str(item.get("anchor") or "")
        if not anc.startswith(("http://", "https://")):
            continue
        buckets.setdefault(anc, []).append(dict(item))

    for refs in buckets.values():
        if len(refs) < 2:
            continue
        a, b = refs[0], refs[1]
        ea = str(a.get("excerpt") or "")
        eb = str(b.get("excerpt") or "")
        if len(ea) < min_excerpt_chars or len(eb) < min_excerpt_chars:
            continue
        jac = consistency.jaccard_similarity(
            consistency.tokenize_normalized(ea),
            consistency.tokenize_normalized(eb),
        )
        if jac <= jaccard_divergence_max:
            conflicts.append(
                _snippet_divergence_conflict(
                    "same_network_anchor_variant_snippets",
                    a,
                    b,
                    note="Distinct snippets were returned for identical HTTP anchors — reconcile primary source text.",
                    verify="Reload the authoritative page revision and compare verbatim spans.",
                )
            )

        if len(conflicts) >= _MAX_CONFLICTS:
            return conflicts[:_MAX_CONFLICTS]

    overlap_set = {consistency_normalize_uri(u) for u in overlapping_http_across_kb_and_web if isinstance(u, str)}
    overlap_set.discard("")
    for u in overlap_set:
        web_rows = [dict(row) for row in items if str(row.get("source_kind")) == "web" and consistency_normalize_uri(str(row.get("anchor") or "")) == u]
        kb_http_rows = [
            dict(row)
            for row in items
            if str(row.get("source_kind")) == "kb"
            and str(row.get("source_uri") or "").startswith(("http://", "https://"))
            and consistency_normalize_uri(str(row.get("source_uri") or "")) == u
        ]
        if not web_rows or not kb_http_rows:
            continue
        w_row, k_row = web_rows[0], kb_http_rows[0]
        ew, ek = str(w_row.get("excerpt") or ""), str(k_row.get("excerpt") or "")
        if len(ew) < min_excerpt_chars or len(ek) < min_excerpt_chars:
            continue
        jac_wk = consistency.jaccard_similarity(
            consistency.tokenize_normalized(ew),
            consistency.tokenize_normalized(ek),
        )
        if jac_wk <= max(jaccard_divergence_max, 0.28):
            conflicts.append(
                _snippet_divergence_conflict(
                    "cross_lane_http_uri_snippet_variance",
                    w_row,
                    k_row,
                    note="KB-derived HTTP anchor content diverges from network tool excerpts — stale snapshot vs live web risk.",
                    verify="Prefer timestamped originals; confirm whether KB ingestion matches observed web revisions.",
                )
            )
        elif jac_wk >= 0.92:
            conflicts.append(
                {
                    "kind": "cross_lane_http_uri_near_duplicate_snapshots",
                    "sources": [
                        {"source_kind": str(w_row["source_kind"]), "anchor": str(w_row["anchor"])},
                        {"source_kind": str(k_row["source_kind"]), "anchor": str(k_row["anchor"])},
                    ],
                    "resolution_status": "low_risk_but_verify_freshness",
                    "risk_note": "Highly similar spans across KB and web lanes may mirror the same retrieval surface.",
                    "verification_suggestion": "Confirm ingestion timestamp plus live page freshness if decisions depend on volatility.",
                }
            )

        if len(conflicts) >= _MAX_CONFLICTS:
            break

    return conflicts[:_MAX_CONFLICTS]


def consistency_normalize_uri(uri: str) -> str:
    return _canonical_http_anchor(uri.strip())


def build_directed_edges(
    normalized_items: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Produce explicit non-causal chain metadata for Inspectability."""

    edges: list[dict[str, Any]] = []
    for idx, item in enumerate(normalized_items, start=1):
        tgt = str(item.get("anchor") or "")
        if not tgt:
            continue
        role = str(item.get("confidence_role") or "")
        strength = "strong" if role == "anchored_quote_baseline" else "weak"

        edges.append(
            {
                "from": "problem_statement",
                "to": tgt,
                "relation_type": "tool_grounding_reference",
                "link_basis": "citation_snapshot_only",
                "link_strength": strength,
                "edge_evidence_basis": "evidence_manifestation",
                **({} if strength == "strong" else {"degraded_reason_codes": ["weak_anchor_metadata"], "escalate_review": True}),
                "ordering_index": idx,
            }
        )
    return edges


def _verification_steps(conflicts: Sequence[Mapping[str, Any]], missing_uri: int, missing_kb: int) -> list[str]:
    steps: list[str] = []

    kinds = {str(c.get("kind")) for c in conflicts if isinstance(c, Mapping)}
    if "cross_lane_http_uri_snippet_variance" in kinds:
        steps.append("Reconcile overlapping HTTP anchors cited by KB vs live web tooling before accepting summaries.")
    if "same_network_anchor_variant_snippets" in kinds:
        steps.append("Deduplicate or canonicalize duplicated network rows with inconsistent snippets.")

    if int(missing_uri or 0) > 0:
        steps.append("Backfill HTTP citations missing URIs — formal merging cannot attest origin traceability.")

    if int(missing_kb or 0) > 0:
        steps.append("Resolve KB citations missing deterministic document/chunk refs for audit replay.")

    if not steps and conflicts:
        steps.append("Review structured conflicts[] — heuristic only; escalate to analyst verdict.")

    return steps


def meta_result_payload(meta_result: MetaAnalysisResult | Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Stable mapping for degraded / review signals."""

    if meta_result is None:
        return {}
    if isinstance(meta_result, MetaAnalysisResult):
        return asdict(meta_result)
    if isinstance(meta_result, Mapping):
        return meta_result
    return {}


def build_evidence_validation_pack(
    *,
    problem_statement: str,
    web_citations: Sequence[Mapping[str, Any]],
    kb_citations: Sequence[Mapping[str, Any]],
    web_stats: Mapping[str, Any],
    kb_stats: Mapping[str, Any],
    overlapping_http_across_kb_and_web: Sequence[str],
    meta_result: MetaAnalysisResult | Mapping[str, Any] | None = None,
    http_refs_summary: Sequence[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Assemble the nested ``validation`` subtree for formal ``analysis_card``."""

    web_list = list(web_citations or [])
    kb_list = list(kb_citations or [])
    meta_map = meta_result_payload(meta_result)

    normalized_items = normalize_evidence_items(web_citations=web_list, kb_citations=kb_list, max_items=_MAX_ITEMS)
    conflicts = derive_conflicts(
        items=normalized_items,
        overlapping_http_across_kb_and_web=overlapping_http_across_kb_and_web or [],
    )
    edges = build_directed_edges(normalized_items)

    excerpt_map: dict[str, str] = {}
    anchors_list: list[str] = []
    for item in normalized_items:
        a = str(item.get("anchor") or "")
        excerpt_map[a] = str(item.get("excerpt") or "")
        anchors_list.append(a)

    pair_candidates: list[tuple[str, str]] = []
    for i, ai in enumerate(anchors_list):
        for bj in anchors_list[i + 1 :]:
            if ai.startswith(("http://", "https://")) and bj.startswith(("http://", "https://")) and ai != bj:
                pair_candidates.append((ai, bj))

    co_hints = consistency.co_occurrence_non_causal_escalation_hints(
        anchor_pairs=pair_candidates,
        excerpts_by_anchor=excerpt_map,
    )

    text_blocks = [problem_statement]
    text_blocks.extend(str(i.get("excerpt") or "") for i in normalized_items)
    temporal = consistency.scan_dense_year_signals(text_blocks)
    temporal.extend(consistency.scan_relative_time_signals(problem_statement, text_blocks))
    temporal.extend(consistency.scan_version_literal_density(text_blocks))
    logic_signals = [*consistency.scan_problem_overclaim_signals(problem_statement)]

    kb_entries = int(kb_stats.get("citation_entry_count") or len(kb_list))
    web_entries = int(web_stats.get("citation_entry_count") or len(web_list))
    web_hosts_hint = len({_host_from_simple_http(uri) for uri in (http_refs_summary or ()) if isinstance(uri, str)})

    policy_hints = [
        *grounding_mix_hints(
            kb_entry_count=kb_entries,
            web_entry_count=web_entries,
            web_distinct_hosts=web_hosts_hint if web_hosts_hint > 0 else int(web_stats.get("unique_network_uris") or 0),
        ),
        *degraded_formal_signals(meta_map),
    ]

    citations_missing_uri = int(web_stats.get("citations_missing_uri") or 0)
    citations_missing_kb = int(kb_stats.get("citations_missing_ref") or 0)
    verification = _verification_steps(conflicts, citations_missing_uri, citations_missing_kb)

    rationale = ""
    lr_raw = meta_map.get("logic_review")
    if isinstance(meta_map.get("method_rationale"), str):
        rationale = meta_map["method_rationale"]

    lr_list: Sequence[str]
    if isinstance(lr_raw, list):
        lr_list = [str(x) for x in lr_raw if isinstance(x, str)]
    elif isinstance(lr_raw, str) and lr_raw.strip():
        lr_list = [lr_raw.strip()]
    else:
        lr_list = []

    rr_raw = meta_map.get("reasonableness_review") or []
    rr_list: Sequence[str]
    if isinstance(rr_raw, list):
        rr_list = [str(x) for x in rr_raw if isinstance(x, str)]
    elif isinstance(rr_raw, str) and rr_raw.strip():
        rr_list = [rr_raw.strip()]
    else:
        rr_list = []

    risks_raw = meta_map.get("risks") or []
    risks_list = [str(x) for x in risks_raw if isinstance(x, str)] if isinstance(risks_raw, list) else []

    inferred_block = {
        "methodology_rationale_excerpt": (rationale.strip()[:400] + ("…" if len(rationale) > 400 else "")).strip(),
        "logic_review_bullets": list(lr_list)[:6],
        "reasonableness_review_bullets": list(rr_list)[:6],
        "risk_bullets": risks_list[:8],
    }

    citation_quotes: list[dict[str, Any]] = []
    for row in normalized_items[:8]:
        ex = str(row.get("excerpt") or "").strip()
        citation_quotes.append(
            {
                "source_kind": row.get("source_kind"),
                "anchor": row.get("anchor"),
                "quoted_excerpt": (ex[:360] + ("…" if len(ex) > 360 else "")) if ex else None,
                "confidence_role": row.get("confidence_role"),
            }
        )

    return {
        "schema": _SCHEMA,
        "normalized_items": normalized_items,
        "conflicts": conflicts,
        "edges": edges,
        "co_occurrence_signals": co_hints,
        "logic_signals": logic_signals,
        "temporal_signals": temporal,
        "policy_hints": policy_hints,
        "delivery": {
            "citation_quotes_for_human_review": citation_quotes,
            "formal_harness_secondary_views": inferred_block,
            "verification_next_steps": verification,
        },
    }


def _host_from_simple_http(uri: str) -> str:
    uri = uri.strip()
    parsed = urlparse(uri)
    return (parsed.hostname or "").lower()


__all__ = [
    "build_directed_edges",
    "build_evidence_validation_pack",
    "consistency_normalize_uri",
    "derive_conflicts",
    "meta_result_payload",
    "normalize_evidence_items",
]
