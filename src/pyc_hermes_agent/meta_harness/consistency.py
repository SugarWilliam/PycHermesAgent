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

_REL_TIME_PHRASES = (
    r"\blast\s+week\b",
    r"\blast\s+month\b",
    r"\byesterday\b",
    r"\b刚刚\b",
    r"\b前天\b",
    r"\b上月\b",
)

_REL_TIME_CRE = re.compile("|".join(f"(?:{p})" for p in _REL_TIME_PHRASES), re.IGNORECASE)

_SEMVER_TOKEN = re.compile(r"\b\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?\b")


def scan_relative_time_signals(problem_statement: str, text_blocks: Sequence[str]) -> list[str]:
    """Flag relative-time language when problem + snippets need explicit calendar anchoring."""

    joined = " ".join(
        blk.strip()
        for blk in [problem_statement, *list(text_blocks)]
        if isinstance(blk, str) and blk.strip()
    )
    if not joined:
        return []
    if _REL_TIME_CRE.search(joined):
        return [
            "relative_time_language_requires_explicit_anchor_clock",
            "Map each relative reference to an absolute window (version, build, or UTC) before concluding timelines.",
        ]
    return []


def scan_version_literal_density(text_blocks: Sequence[str]) -> list[str]:
    """Heuristic: many distinct semver tokens in compact snippets → reconcile release ordering manually."""

    tokens: list[str] = []

    seen: set[str] = set()
    blob = "\n".join(b for b in text_blocks if isinstance(b, str) and b.strip())
    if not blob:
        return []

    for m in _SEMVER_TOKEN.finditer(blob):
        tok = m.group(0)

        if tok not in seen:
            seen.add(tok)
            tokens.append(tok)

        if len(tokens) >= 4 and len(blob) <= 560:
            return [
                "multiple_distinct_versions_in_compact_context",
                "Confirm whether cited versions coexist, supersede each other, or reference different SKU lines.",
            ]

    return []


def scan_wide_percentage_conflict_within_blocks(text_blocks: Sequence[str], *, gap: int = 40, max_chars: int = 420) -> list[str]:
    """If a *single short* excerpt lists percentages far apart, ask humans to reconcile (non-prover)."""

    pct_re = re.compile(r"\b(\d{1,3})%")

    hints: list[str] = []

    for blk in text_blocks:
        if not isinstance(blk, str):
            continue
        text = blk.strip()

        if not text or len(text) > max_chars:
            continue

        nums = [int(m.group(1)) for m in pct_re.finditer(text)]

        if len(nums) < 2:

            continue

        spread = max(nums) - min(nums)

        if spread >= gap:
            uniq = ",".join(str(n) for n in sorted(set(nums)))
            hints.extend(
                [
                    "wide_percentage_spread_inside_single_snippet_requires_manual_calibration",
                    f"percents_seen={uniq}; spread>= {gap}",
                ]
            )

            break

    return hints


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


# Compact IPC / surveillance specs often mention multiple incompatible output profiles — flag for human review only.
_RES_TOKEN_RE = re.compile(
    r"\b(?:"
    r"1080p|720p|480p|"
    r"4k|2160p|4320p|"
    r"1920\s*[x×]1080|1280\s*[x×]720|3840\s*[x×]2160|2560\s*[x×]1440|2592\s*[x×]1944"
    r")\b",
    re.IGNORECASE,
)

# Millisecond latency numbers in competing narrative arcs (marketing vs bench note).
_LATENCY_MS_RE = re.compile(r"\b(\d{2,5})\s*ms\b", re.IGNORECASE)

_ONVIF_RE = re.compile(r"\bonvif\b", re.IGNORECASE)
_PROPRIETARY_ONLY_RE = re.compile(
    r"(?:"
    r"proprietary\s+only|"
    r"vendor[- ]?locked|"
    r"closed\s+protocol|"
    r"\bpure\b\s*\bprivate\b|"
    r"封闭式|封闭协议"
    r")",
    re.IGNORECASE,
)


def _resolution_bucket(tok: str) -> str | None:
    """Map surface tokens onto coarse buckets — two buckets in one short block ⇒ profile conflict hint."""

    t = re.sub(r"\s+", "", tok.lower()).replace("×", "x")

    hd1080_aliases = frozenset({"1080p", "1920x1080"})
    hd720_aliases = frozenset({"720p", "1280x720"})
    uhd_aliases = frozenset({"2160p", "3840x2160", "4k"})
    uhd8_aliases = frozenset({"4320p"})

    if t in hd1080_aliases:
        return "bucket_1080p"
    if t in hd720_aliases:
        return "bucket_720p"
    if t in uhd_aliases:
        return "bucket_uhd2160"
    if t in uhd8_aliases:
        return "bucket_uhd4320"
    if re.fullmatch(r"\d{3,5}x\d{3,5}", t):
        return f"bucket_wh_{t}"
    return None


def scan_mutex_video_resolution_tokens(
    text_blocks: Sequence[str], *, max_block_chars: int = 520
) -> list[str]:
    """Multiple distinct codec/output profile mentions in one short snippet."""

    for blk in text_blocks:
        if not isinstance(blk, str):
            continue
        text = blk.strip()

        if not text or len(text) > max_block_chars:
            continue

        buckets: set[str] = set()
        for m in _RES_TOKEN_RE.finditer(text):
            b = _resolution_bucket(m.group(0))

            if b:
                buckets.add(b)

            if len(buckets) >= 2:
                ordered = tuple(sorted(buckets))
                return [
                    "mutex_video_resolution_tokens_single_snippet_ipc_review",
                    f"distinct_resolution_profiles_seen={ordered} — confirm one effective encode/decode/stream path.",
                    "edge_escalation=do_not_select_output_profile_without_device_capability_matrix",
                ]

    return []


def scan_competing_latency_ms_claims(
    text_blocks: Sequence[str],
    *,
    max_block_chars: int = 620,
    min_spread_ms: int = 150,
    min_claims: int = 2,
) -> list[str]:
    """Two+ ms timings in one short excerpt with wide spread → reconcile measurement methodology."""

    for blk in text_blocks:
        if not isinstance(blk, str):
            continue
        text = blk.strip()

        if not text or len(text) > max_block_chars:
            continue

        nums = [int(x) for x in _LATENCY_MS_RE.findall(text)]

        if len(nums) < min_claims:
            continue

        lo, hi = min(nums), max(nums)

        if hi - lo >= min_spread_ms:
            return [
                "competing_latency_ms_narratives_in_short_snippet",
                f"latency_ms_seen={sorted(set(nums))} spread={hi - lo} — scope (LAN/WAN/device path) unspecified.",
                "edge_escalation=do_not_merge_percentiles_into_single_sla_claim",
            ]

    return []


def scan_onvif_proprietary_mutex_language(text_blocks: Sequence[str], *, max_block_chars: int = 840) -> list[str]:
    """ONVIF interoperability language colliding with 'proprietary-only' storyline in same window."""

    for blk in text_blocks:
        if not isinstance(blk, str):
            continue
        text = blk.strip()

        if not text or len(text) > max_block_chars:
            continue

        if _ONVIF_RE.search(text) and _PROPRIETARY_ONLY_RE.search(text):
            return [
                "onvif_vs_proprietary_mutex_language_ipc_review",
                "Snippet couples ONVIF with proprietary-only framing — reconcile transport/profile vs vendor stacks.",
                "edge_escalation=do_not_equate_optional_profile_support_with_closed_protocol_claims_without_SKU_facts",
            ]

    return []
