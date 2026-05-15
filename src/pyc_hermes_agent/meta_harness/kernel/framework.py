"""Minimal MetaFramework entry point for formal analysis."""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from pyc_hermes_agent.contracts import MetaAnalysisRequest, MetaAnalysisResult
from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge
from pyc_hermes_agent.meta_harness.judge.review import MethodJudge
from pyc_hermes_agent.meta_harness.quality.checks import QualityChecker
from pyc_hermes_agent.meta_harness.registry.catalog import CapabilityRegistry
from pyc_hermes_agent.meta_harness.router.selector import MethodSelector


class MetaFramework:
    """Stable formal-analysis entry point."""

    def __init__(self) -> None:
        self.registry = CapabilityRegistry()
        self.selector = MethodSelector(self.registry)
        self.judge = MethodJudge()
        self.quality = QualityChecker()
        self.bridge = LegacyMetaBridge()

    def execute(self, request: MetaAnalysisRequest) -> MetaAnalysisResult:
        selected = self.selector.select(request)
        execution_details = self._execute_selected_method(request, selected)
        degraded = selected is None or self._is_execution_degraded(execution_details)
        result = MetaAnalysisResult(
            selected_method=selected.id if selected else "manual-review",
            method_rationale=self.selector.explain(request, selected),
            assumptions=self.selector.assumptions(request, selected),
            logic_review=self.judge.logic_review(request, selected),
            reasonableness_review=self.judge.reasonableness_review(request, selected),
            evidence_grade=selected.max_evidence_grade if selected else "CE-C1",
            sr_grade="SR-C1",
            degraded=degraded,
            risks=self.quality.risks(request, selected),
            recommendations=self.quality.recommendations(request, selected),
            execution_details=execution_details,
        )
        self.quality.annotate_execution(result)
        self.quality.validate(result)
        return result

    def execute_dict(self, request: MetaAnalysisRequest) -> dict:
        return asdict(self.execute(request))

    def _execute_selected_method(self, request: MetaAnalysisRequest, selected: Optional[object]) -> dict:
        if selected is None:
            return {"status": "not_run", "reason": "No method selected."}
        if not request.data:
            return {"status": "not_run", "reason": "No execution payload supplied."}
        return self.bridge.execute(selected.id, request.data, request.params)

    @staticmethod
    def _is_execution_degraded(execution_details: dict) -> bool:
        if not execution_details:
            return False
        if execution_details.get("status") == "not_run":
            return False
        if execution_details.get("validated") is False:
            return True
        if execution_details.get("error"):
            return True
        return False
