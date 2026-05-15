"""Logic and reasonableness review helpers."""

from __future__ import annotations

from typing import Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest


class MethodJudge:
    def logic_review(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if selected is None:
            return ["Formal logic review incomplete because no methodology was selected."]
        return [
            f"Method {selected.id} remains within its current evidence ceiling of {selected.max_evidence_grade}.",
            "Formal claims must remain within the selected method's evidence scope.",
        ]

    def reasonableness_review(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if selected is None:
            return ["Reasonableness review recommends narrowing the problem statement."]
        return [
            "The selected method is a high-level route and not yet a proof of data adequacy.",
            "Predictive findings must not be escalated to intervention-grade claims without additional evidence.",
        ]
