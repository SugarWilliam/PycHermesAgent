"""Minimum quality checks for formal analysis responses."""

from __future__ import annotations

from typing import Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest, MetaAnalysisResult


class QualityChecker:
    def risks(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        risks = []
        if selected is None:
            risks.append("No formal method selected; analysis is degraded.")
        elif selected.max_evidence_grade == "CE-C1":
            risks.append("Selected route is predictive-first and must not be presented as strong causal proof.")
        return risks

    def recommendations(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if selected is None:
            return ["Clarify task scope or provide stronger domain hints before formal execution."]
        if selected.id == "A-12-SCM":
            return ["Provide structured data, cause/effect fields, and identification assumptions."]
        return ["Proceed with detailed data adequacy and bridge-level execution checks."]

    def annotate_execution(self, result: MetaAnalysisResult) -> None:
        status = result.execution_details.get("status")
        error = result.execution_details.get("error")
        if status == "not_run":
            return
        if error:
            result.risks.append(f"Execution bridge reported: {error}")
        if result.execution_details.get("validated") is False and "degraded" not in result.recommendations:
            result.recommendations.append("Resolve bridge dependencies or inputs before relying on formal execution output.")

    def validate(self, result: MetaAnalysisResult) -> None:
        if not result.selected_method and not result.degraded:
            raise ValueError("A non-degraded formal result must include a selected method.")
