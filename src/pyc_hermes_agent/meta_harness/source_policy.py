"""Phase 3F1 — declarative source-class hints for grounded formal analysis.

This module encodes **question-aware precedence guidance** only (no silent ranking applied to
claims). Consumers attach ``policy_hints[]`` under ``analysis_card.evidence_chain.validation`` for
explainability."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Narrative anchors for downstream UX — not machine-enforced truth ordering.
ENGINEERING_DIAGNOSTIC_HINT = (
    "For engineering correctness questions, prioritize code/runtime/config anchors over fragmented web snippets "
    "when both exist (policy guidance only — reviewers must reconcile)."
)

PRODUCT_REFERENCE_HINT = "For curated product reference facts, prefer structured KB grounding over conversational-only recall (policy guidance only)."

MULTI_LOW_DIVERSITY = "Multiple network hosts with low breadth can still miss authoritative primary sources — verify originals."


def grounding_mix_hints(*, kb_entry_count: int, web_entry_count: int, web_distinct_hosts: int) -> list[str]:
    """Return short policy strings given coarse citation histograms."""

    hints: list[str] = []

    kb_e = max(0, int(kb_entry_count))
    web_e = max(0, int(web_entry_count))
    hosts = max(0, int(web_distinct_hosts))

    if kb_e > 0 and web_e > 0:
        hints.extend([ENGINEERING_DIAGNOSTIC_HINT, PRODUCT_REFERENCE_HINT])

    elif kb_e == 0 and web_e >= 6 and hosts <= 2:
        hints.append(MULTI_LOW_DIVERSITY)

    elif kb_e >= 8 and web_e == 0:
        hints.append("KB-only grounding: strong for curated corpora — confirm KB coverage spans the asserted scope.")

    return hints


def degraded_formal_signals(meta_result: Mapping[str, Any] | None) -> list[str]:
    """Surface harness-level degraded hints without interpreting CE/SR grades."""

    out: list[str] = []
    if not isinstance(meta_result, Mapping):
        return out
    if bool(meta_result.get("degraded")):
        out.append("meta_harness_reports_degraded_execution_or_selection")
        out.append("Treat formal summaries as brittle until degraded reasons are inspected (see risks / execution_details).")
    return out
