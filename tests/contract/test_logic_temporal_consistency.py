"""Contract tests for Phase 3F1 consistency heuristics (logic + temporal signals)."""

from __future__ import annotations

from pyc_hermes_agent.meta_harness import consistency


def test_problem_overclaim_regex_fires() -> None:
    sigs = consistency.scan_problem_overclaim_signals("This dataset proved causation without doubt today.")
    assert "problem_statement_possible_causal_overclaim_lexical_hint" in sigs


def test_dense_year_signal_on_compact_text() -> None:
    blob = " ".join(["Event in 1999", "then 2005", "peak 2011", "sunset 2018"])
    out = consistency.scan_dense_year_signals([blob, "short"])
    assert any("dense_calendar_years" in s or "year" in s for s in out)


def test_co_occurrence_high_overlap_is_non_causal_warning_only() -> None:
    a = "https://a.example/p1"
    b = "https://b.example/p2"
    long_excerpt = (
        "the quick brown fox jumps over the lazy dog repeatedly while engineers discuss deployment safety checks"
    )
    hints = consistency.co_occurrence_non_causal_escalation_hints(
        anchor_pairs=[(a, b)],
        excerpts_by_anchor={a: long_excerpt, b: long_excerpt + " today"},
        jaccard_floor=0.80,
    )
    assert hints
    assert hints[0]["edge_escalation"] == "do_not_infer_causal_link_from_lexical_overlap"


def test_jaccard_extremes() -> None:
    assert consistency.jaccard_similarity(frozenset(), frozenset()) == 1.0
    left = consistency.tokenize_normalized("alpha beta gamma")
    right = consistency.tokenize_normalized("alpha beta delta")
    j = consistency.jaccard_similarity(left, right)
    assert 0.3 < j < 0.8
