"""Phase 3F1 — heuristic logic / temporal consistency scans (non-prover, non-causal).

Flags **review prompts** derived from lexical patterns in problem statements + citation excerpts.

These checks must never invent adjudicated conclusions; callers merge ``signals[]`` only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

# Year-like tokens — conservative to avoid IDs like 202412.
_YEAR_RE = re.compile(r"\b(19\d{2}|20[0-3]\d)\b")

# Loose causal-absolutism / overclaim tails (engineering safety net).
_CAUSAL_ABSOLUTES = (
    r"\bproved\s+caus",
    r"\bestablishes\s+caus",
    r"\bguarantees\s+that\b",
    r"\bwithout\s+(any\s+)?(doubt|risk)",
    r"\balways\b.*\bcause\b",
)
_CAUSAL_ABSOLUTE_CRE = re.compile("|".join(f"(?:{p})" for p in _CAUSAL_ABSOLUTES), re.IGNORECASE)

# Mirrors / duplication risk between independent URIs (co-occurrence ≠ causation wording).
_NEAR_DUP_NOTE = "High lexical overlap across different anchors may indicate mirrored summaries — do not infer agreement."


def tokenize_normalized(text: str) -> frozenset[str]:
    """Lower-case word-ish tokens."""

    return frozenset(t for t in re.findall(r"[a-z0-9]{2,}", text.lower()) if t)


def jaccard_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    """Jaccard on token sets."""

    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    inter = len(left & right)
    union = len(left | right)
    return float(inter) / float(union) if union else 0.0


def scan_problem_overclaim_signals(problem_statement: str) -> list[str]:
    """Warn when wording demands causal proof without hedging anchors."""

    if not problem_statement or not problem_statement.strip():
        return []
    text = problem_statement.strip()
    if _CAUSAL_ABSOLUTE_CRE.search(text):
        return [
            "problem_statement_possible_causal_overclaim_lexical_hint",
            "Verify whether evidence scope supports mandatory causal wording (prefer SR / CE reviews).",
        ]
    return []


def scan_dense_year_signals(text_blocks: Sequence[str]) -> list[str]:
    """Flag many distinct calendar years squeezed into grounding snippets."""

    years: list[str] = []
    seen: set[str] = set()
    for blk in text_blocks:
        if not isinstance(blk, str):
            continue
        for m in _YEAR_RE.finditer(blk):
            y = m.group(1)
            if y not in seen:
                seen.add(y)
                years.append(y)
    blocks = [b.strip() for b in text_blocks if isinstance(b, str) and b.strip()]
    avg_len = (sum(len(b) for b in blocks) / len(blocks)) if blocks else 0.0
    distinct = len(set(years))
    signals: list[str] = []

    if distinct >= 4 and avg_len and avg_len <= 560:
        signals.append("dense_calendar_years_review_timeline_explicitly")

    elif distinct >= 6:
        signals.append("high_year_token_count_requires_chronological_reconciliation")

    return signals


def co_occurrence_non_causal_escalation_hints(
    *,
    anchor_pairs: Sequence[tuple[str, str]],
    excerpts_by_anchor: Mapping[str, str],
    jaccard_floor: float = 0.86,
    min_excerpt_len: int = 80,
) -> list[dict[str, Any]]:
    """Surface **non-causal** warnings when excerpts look duplicative across distinct anchors."""

    notes: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    def _canonical(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    for pa, pb in anchor_pairs:
        if not isinstance(pa, str) or not isinstance(pb, str):
            continue
        aa, bb = pa.strip(), pb.strip()
        if not aa or not bb or aa == bb:
            continue
        canon = _canonical(aa, bb)
        if canon in seen_pairs:
            continue
        seen_pairs.add(canon)
        xa = excerpts_by_anchor.get(pa, excerpts_by_anchor.get(aa, "")) or ""
        xb = excerpts_by_anchor.get(pb, excerpts_by_anchor.get(bb, "")) or ""
        xa_s, xb_s = str(xa).strip(), str(xb).strip()
        if len(xa_s) < min_excerpt_len or len(xb_s) < min_excerpt_len:
            continue
        jac = jaccard_similarity(tokenize_normalized(xa_s), tokenize_normalized(xb_s))
        if jac >= jaccard_floor:
            notes.append(
                {
                    "kind": "co_occurrence_near_duplicate_summaries_only",
                    "anchors": sorted([aa, bb]),
                    "note": _NEAR_DUP_NOTE,
                    "edge_escalation": "do_not_infer_causal_link_from_lexical_overlap",
                }
            )
    return notes
