"""Contract coverage for Phase 3F1 ``meta_harness.evidence_chain`` (structured validation payloads)."""

from __future__ import annotations

from pyc_hermes_agent.contracts import MetaAnalysisResult
from pyc_hermes_agent.meta_harness.evidence_chain import (
    build_directed_edges,
    build_evidence_validation_pack,
    derive_conflicts,
    normalize_evidence_items,
)


def test_normalize_keeps_kb_before_web_budget() -> None:
    kb = [{"document_id": "d", "chunk_id": "c", "snippet": "alpha bravo"}, {"document_id": "d2", "chunk_id": "c2"}]
    web = [{"source_uri": "https://example.com/q", "snippet": "gamma"}]
    items = normalize_evidence_items(web_citations=web, kb_citations=kb, max_items=2)
    assert len(items) == 2
    assert items[0]["source_kind"] == "kb"
    assert items[1]["source_kind"] == "kb"


def test_same_network_anchor_variant_snippets_conflict() -> None:
    u = "https://example.com/a"
    items = normalize_evidence_items(
        web_citations=[
            {"source_uri": u, "snippet": "completely different long snippet one about widgets"},
            {"source_uri": u, "snippet": "another topic entirely about galaxy formation details"},
        ],
        kb_citations=[],
        max_items=40,
    )
    conflicts = derive_conflicts(items=items, overlapping_http_across_kb_and_web=[])
    kinds = {c.get("kind") for c in conflicts}
    assert "same_network_anchor_variant_snippets" in kinds


def test_cross_lane_overlap_snippet_variance() -> None:
    overlap = "https://overlap.example/o1"
    items = normalize_evidence_items(
        web_citations=[{"source_uri": overlap, "snippet": "live web summary about topic alpha delta"}],
        kb_citations=[
            {
                "document_id": "doc1",
                "chunk_id": "k1",
                "source_uri": overlap,
                "snippet": "archived kb copy discusses unrelated beta epsilon zeta completely",
            }
        ],
        max_items=40,
    )
    conflicts = derive_conflicts(items=items, overlapping_http_across_kb_and_web=[overlap])
    kinds = {c.get("kind") for c in conflicts}
    assert "cross_lane_http_uri_snippet_variance" in kinds


def test_weak_edge_metadata_on_short_excerpts() -> None:
    items = normalize_evidence_items(
        web_citations=[{"source_uri": "https://a.example/x", "snippet": "short"}],
        kb_citations=[],
    )
    edges = build_directed_edges(items)
    assert edges and edges[0]["link_strength"] == "weak"
    assert edges[0].get("escalate_review") is True


def test_build_pack_includes_schema_and_policy_hints() -> None:
    pack = build_evidence_validation_pack(
        problem_statement="Compare runtime notes",
        web_citations=[{"source_uri": "https://a.example/x", "snippet": "network evidence line one two three four five"}],
        kb_citations=[{"document_id": "d", "chunk_id": "c", "snippet": "kb line one two three four five"}],
        web_stats={"citation_entry_count": 1, "unique_network_uris": 1, "aggregated_uri_rows_before_dedupe": 1},
        kb_stats={"citation_entry_count": 1, "distinct_documents": 1, "citations_missing_ref": 0},
        overlapping_http_across_kb_and_web=[],
        meta_result=MetaAnalysisResult(
            selected_method="m",
            method_rationale="r",
            degraded=False,
            logic_review=["logic note"],
        ),
        http_refs_summary=("https://a.example/x",),
    )
    assert pack["schema"] == "phase3f1/evidence-validation/v1"
    assert pack["normalized_items"]
    assert any("engineering" in h.lower() or "kb" in h.lower() for h in pack["policy_hints"])
    assert pack["delivery"]["formal_harness_secondary_views"]["logic_review_bullets"] == ["logic note"]


def test_degraded_meta_surfaces_policy_signal() -> None:
    pack = build_evidence_validation_pack(
        problem_statement="x",
        web_citations=[],
        kb_citations=[],
        web_stats={"citation_entry_count": 0},
        kb_stats={"citation_entry_count": 0},
        overlapping_http_across_kb_and_web=[],
        meta_result=MetaAnalysisResult(degraded=True),
    )
    joined = " ".join(pack["policy_hints"]).lower()
    assert "degraded" in joined
