"""Phase 3F1-style network evidence summaries (hints only — not CE/SR)."""

from __future__ import annotations

from pyc_hermes_agent.meta_harness.evidence_hints import (
    summarize_formal_multi_source_evidence_chain,
    summarize_network_evidence_chain,
)


def test_summarize_hints_flag_single_host_diversity_when_many_uris_share_host() -> None:
    refs = [
        "https://example.com/a",
        "https://example.com/b",
    ]
    out = summarize_network_evidence_chain(
        network_refs=refs,
        citation_entries_total=2,
        unique_network_uris=2,
        aggregated_uri_rows_before_dedupe=2,
    )
    assert "network_evidence_single_host_only" in out["hints"]


def test_summarize_hints_dedupe_when_pre_dedupe_rows_exceed_unique() -> None:
    refs = ["https://a.example/x"]
    out = summarize_network_evidence_chain(
        network_refs=refs,
        citation_entries_total=2,
        unique_network_uris=1,
        aggregated_uri_rows_before_dedupe=3,
    )
    assert "network_uri_rows_deduplicated" in out["hints"]


def test_summarize_formal_detects_kb_web_multi_source_hint() -> None:
    merged = summarize_formal_multi_source_evidence_chain(
        http_refs=["https://a.example/z"],
        web_stats={
            "citation_entry_count": 1,
            "unique_network_uris": 1,
            "aggregated_uri_rows_before_dedupe": 1,
        },
        kb_stats={"citation_entry_count": 1, "distinct_documents": 1, "citations_missing_ref": 0},
        overlapping_http_across_kb_and_web=[],
    )
    assert "multi_source_web_and_kb_grounding" in merged["hints"]

