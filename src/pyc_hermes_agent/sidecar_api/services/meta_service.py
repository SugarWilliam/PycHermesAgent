"""MetaHarness formal analysis service functions."""

from __future__ import annotations

from typing import Any, Dict

from pyc_hermes_agent.contracts import MetaAnalysisRequest, TaskResult
from pyc_hermes_agent.meta_harness import MetaFramework
from pyc_hermes_agent.meta_harness.benchmark import run_value_proof_benchmark
from pyc_hermes_agent.sidecar_api.error_domains import DOMAIN_META_HARNESS
from pyc_hermes_agent.sidecar_api.services.common import (
    _event,
    _serialize,
    make_error_response,
)


def invoke_formal_analysis(request: MetaAnalysisRequest) -> Dict[str, Any]:
    framework = MetaFramework()
    task_id = request.problem_statement[:32] or "formal-analysis"
    started = _event("sidecar", "task.started", task_id, {"mode": "formal-analysis"})
    try:
        result = framework.execute(request)
        finished = _event(
            "sidecar",
            "task.finished",
            task_id,
            {
                "selected_method": result.selected_method,
                "degraded": result.degraded,
                "evidence_grade": result.evidence_grade,
            },
        )
        task_result = TaskResult(
            task_id=task_id,
            status="degraded" if result.degraded else "success",
            summary=result.method_rationale,
            outputs=[{"meta_analysis": _serialize(result)}],
            warnings=result.risks,
            trace_ref=result.selected_method or None,
        )
        return {
            "events": [started, finished],
            "result": _serialize(task_result),
            "analysis": _serialize(result),
        }
    except Exception as exc:
        failure = _event("sidecar", "task.failed", task_id, {"mode": "formal-analysis"})
        response = make_error_response(
            "FORMAL_ANALYSIS_FAILED",
            "internal",
            str(exc),
            domain=DOMAIN_META_HARNESS,
            degraded=False,
        )
        response["events"] = [started, failure]
        return response


def get_meta_harness_dependency_snapshot() -> Dict[str, Any]:
    return MetaFramework().dependency_snapshot()


def get_meta_harness_benchmark_smoke() -> Dict[str, Any]:
    return MetaFramework().run_benchmark_smoke()


def get_meta_harness_value_proof_benchmark() -> Dict[str, Any]:
    return run_value_proof_benchmark()
