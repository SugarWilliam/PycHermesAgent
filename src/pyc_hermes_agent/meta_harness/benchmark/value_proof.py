"""Compare a simulated LLM-only baseline against MetaHarness-guided formal analysis.

This satisfies Phase 1D's need for benchmark evidence without requiring provider calls.
The baseline models an assistant path that does not run ``MetaFramework.execute()``.
"""

from __future__ import annotations

from typing import Any, Optional

from pyc_hermes_agent.contracts import MetaAnalysisRequest
from pyc_hermes_agent.meta_harness.kernel.framework import MetaFramework
from pyc_hermes_agent.meta_harness.quality.checks import (
    request_has_overclaim_language,
    risks_include_overclaim_guardrail,
)


def baseline_llm_stub(request: MetaAnalysisRequest) -> dict[str, Any]:
    """Stub for answers that never invoke the formal harness pipeline."""
    return {
        "paradigm": "llm_only_stub",
        "formal_method_id": None,
        "structured_risks": [],
        "user_prompt_has_overclaim_language": request_has_overclaim_language(request),
        "notes": "No method routing, dependency snapshot, or quality.merge with MetaFramework.",
    }


def _guided_snapshot(request: MetaAnalysisRequest, framework: MetaFramework) -> dict[str, Any]:
    result = framework.execute(request)
    return {
        "paradigm": "meta_harness_guided",
        "formal_method_id": result.selected_method,
        "structured_risks": list(result.risks),
        "degraded": result.degraded,
        "evidence_grade": result.evidence_grade,
        "execution_digest": {
            "status": result.execution_details.get("status"),
            "validated": result.execution_details.get("validated"),
        },
    }


def _default_cases() -> list[tuple[str, MetaAnalysisRequest]]:
    return [
        (
            "overclaim_language",
            MetaAnalysisRequest(problem_statement="proved causation with certainty about churn"),
        ),
        (
            "graph_shape_routing",
            MetaAnalysisRequest(
                problem_statement="map influence given the graph",
                data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            ),
        ),
        (
            "team_dependency_visibility",
            MetaAnalysisRequest(problem_statement="团队冲突与生产力分析"),
        ),
        (
            "degraded_manual_review",
            MetaAnalysisRequest(problem_statement="do something unspecified"),
        ),
    ]


def run_value_proof_benchmark(
    framework: Optional[MetaFramework] = None,
    *,
    cases: Optional[list[tuple[str, MetaAnalysisRequest]]] = None,
) -> dict[str, Any]:
    """Run baseline vs guided comparison on fixed scenarios; returns aggregate metrics."""
    fw = framework or MetaFramework()
    rows: list[dict[str, Any]] = []
    guided_overclaim_detections = 0
    baseline_silent_overclaim = 0
    graph_routes_a22 = 0
    dependency_risk_surfaces = 0
    guided_non_manual = 0

    for case_id, request in cases or _default_cases():
        baseline = baseline_llm_stub(request)
        guided = _guided_snapshot(request, fw)

        user_overclaim = baseline["user_prompt_has_overclaim_language"]
        guided_overclaim = risks_include_overclaim_guardrail(guided["structured_risks"])
        delta = user_overclaim and guided_overclaim and not baseline["structured_risks"]

        if user_overclaim and not baseline["structured_risks"]:
            baseline_silent_overclaim += 1
        if guided_overclaim:
            guided_overclaim_detections += 1
        if case_id == "graph_shape_routing" and guided["formal_method_id"] == "A-22":
            graph_routes_a22 += 1
        if case_id == "team_dependency_visibility" and any(
            "org_personal_adapters" in item for item in guided["structured_risks"]
        ):
            dependency_risk_surfaces += 1
        if guided["formal_method_id"] not in (None, "", "manual-review"):
            guided_non_manual += 1

        rows.append(
            {
                "case_id": case_id,
                "baseline": baseline,
                "guided": guided,
                "signals": {
                    "guided_flags_overclaim_vs_baseline_silent": delta,
                },
            }
        )

    aggregate = {
        "guided_overclaim_detection_cases": guided_overclaim_detections,
        "baseline_silent_despite_overclaim_phrase_cases": baseline_silent_overclaim,
        "graph_routes_a22_cases": graph_routes_a22,
        "dependency_risk_surface_cases": dependency_risk_surfaces,
        "guided_non_manual_selection_cases": guided_non_manual,
    }

    passed = (
        guided_overclaim_detections >= 1
        and graph_routes_a22 == 1
        and dependency_risk_surfaces == 1
        and any(row["signals"]["guided_flags_overclaim_vs_baseline_silent"] for row in rows)
    )

    return {
        "entrypoint": "MetaFramework.execute",
        "benchmark_id": "meta_harness.value_proof.v1",
        "scenario_count": len(rows),
        "cases": rows,
        "aggregate": aggregate,
        "passed": passed,
    }
