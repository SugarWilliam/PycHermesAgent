"""Minimal MetaFramework entry point for formal analysis."""

from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest, MetaAnalysisResult
from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge
from pyc_hermes_agent.meta_harness.judge.review import MethodJudge
from pyc_hermes_agent.meta_harness.quality.checks import QualityChecker
from pyc_hermes_agent.meta_harness.registry.catalog import CapabilityRegistry
from pyc_hermes_agent.meta_harness.router.selector import MethodSelector


class MetaFramework:
    """Stable formal-analysis entry point."""

    def __init__(self) -> None:
        self.bridge = LegacyMetaBridge()
        self.registry = CapabilityRegistry(self.bridge)
        self.selector = MethodSelector(self.registry, self.bridge)
        self.judge = MethodJudge()
        self.quality = QualityChecker()

    def execute(self, request: MetaAnalysisRequest) -> MetaAnalysisResult:
        selected = self.selector.select(request)
        execution_details = self._execute_selected_method(request, selected)
        degraded = selected is None or self._is_execution_degraded(execution_details)
        base_risks = list(self.quality.risks(request, selected))
        base_risks.extend(self._dependency_risk_notes(selected))
        result = MetaAnalysisResult(
            selected_method=selected.id if selected else "manual-review",
            method_rationale=self.selector.explain(request, selected, bridge=self.bridge),
            assumptions=self.selector.assumptions(request, selected),
            logic_review=self.judge.logic_review(request, selected),
            reasonableness_review=self.judge.reasonableness_review(request, selected),
            evidence_grade=selected.max_evidence_grade if selected else "CE-C1",
            sr_grade="SR-C1",
            degraded=degraded,
            risks=base_risks,
            recommendations=self.quality.recommendations(request, selected),
            execution_details=execution_details,
        )
        self.quality.annotate_execution(result)
        self.quality.validate(result)
        return result

    def execute_dict(self, request: MetaAnalysisRequest) -> dict:
        return asdict(self.execute(request))

    def dependency_snapshot(self) -> dict:
        capabilities = []
        for capability in sorted(self.registry.all(), key=lambda item: item.id):
            dependencies = []
            for dependency in capability.dependencies:
                status = self.bridge.status(dependency)
                dependencies.append(
                    {
                        "name": dependency,
                        "available": status.available,
                        "path": str(status.path) if status.path is not None else "",
                        "error": status.error or "",
                    }
                )
            capabilities.append(
                {
                    "id": capability.id,
                    "kind": capability.kind,
                    "max_evidence_grade": capability.max_evidence_grade,
                    "dependencies": dependencies,
                    "available": all(dependency["available"] for dependency in dependencies),
                }
            )
        return {
            "entrypoint": "MetaFramework.execute",
            "capability_count": len(capabilities),
            "capabilities": capabilities,
        }

    def run_benchmark_smoke(self) -> dict:
        cases = [
            MetaAnalysisRequest(
                problem_statement="network pagerank smoke benchmark",
                data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
                params={"analysis": "pagerank"},
            ),
            MetaAnalysisRequest(problem_statement="因果分析：X 对 Y 的影响"),
            MetaAnalysisRequest(problem_statement="please do something vague"),
            MetaAnalysisRequest(
                problem_statement="forecast next quarter demand from history",
                data={"series": [1.0, 1.2, 1.1, 1.4]},
            ),
            MetaAnalysisRequest(
                problem_statement="proved causation with certainty in operations",
                data={},
            ),
            MetaAnalysisRequest(
                problem_statement="network diffusion without payload is invalid for A-22",
                data={},
                params={},
            ),
        ]
        results = []
        failed_count = 0
        for index, request in enumerate(cases, start=1):
            started = perf_counter()
            try:
                result = self.execute(request)
                results.append(
                    {
                        "case_id": f"smoke-{index}",
                        "selected_method": result.selected_method,
                        "degraded": result.degraded,
                        "evidence_grade": result.evidence_grade,
                        "duration_ms": round((perf_counter() - started) * 1000, 3),
                        "error": "",
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive smoke wrapper
                failed_count += 1
                results.append(
                    {
                        "case_id": f"smoke-{index}",
                        "selected_method": "",
                        "degraded": True,
                        "evidence_grade": "",
                        "duration_ms": round((perf_counter() - started) * 1000, 3),
                        "error": str(exc),
                    }
                )
        return {
            "entrypoint": "MetaFramework.execute",
            "case_count": len(results),
            "failed_count": failed_count,
            "passed": failed_count == 0,
            "cases": results,
        }

    def _dependency_risk_notes(self, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if selected is None:
            return []
        notes: list[str] = []
        for dependency in selected.dependencies:
            status = self.bridge.status(dependency)
            if not status.available:
                err = status.error or "unavailable"
                notes.append(f"Formal dependency '{dependency}' is unavailable: {err}")
        return notes

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
