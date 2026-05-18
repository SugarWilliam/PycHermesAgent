"""Method selection with data-shape preconditions and dependency-aware scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest
from pyc_hermes_agent.meta_harness.registry.catalog import CapabilityRegistry
from pyc_hermes_agent.meta_harness.router.preconditions import capability_preconditions_met

if TYPE_CHECKING:
    from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge


@dataclass(slots=True)
class CandidateScore:
    capability: CapabilityDescriptor
    score: int
    deps_satisfied: int


class MethodSelector:
    def __init__(self, registry: CapabilityRegistry, bridge: LegacyMetaBridge | None = None) -> None:
        self.registry = registry
        self._bridge = bridge

    def _dependency_penalty(self, capability: CapabilityDescriptor) -> int:
        if self._bridge is None:
            return 0
        penalty = 0
        for dependency in capability.dependencies:
            if not self._bridge.status(dependency).available:
                penalty += 4
        return penalty

    def _deps_satisfied_count(self, capability: CapabilityDescriptor) -> int:
        if self._bridge is None:
            return len(capability.dependencies)
        return sum(1 for d in capability.dependencies if self._bridge.status(d).available)

    def select(self, request: MetaAnalysisRequest) -> Optional[CapabilityDescriptor]:
        text = request.problem_statement.lower()
        candidates: list[CandidateScore] = []

        for capability in self.registry.all():
            if not capability_preconditions_met(capability.id, request):
                continue

            score = 0

            if capability.id == "A-12-SCM" and any(
                token in text for token in ("causal", "因果", "instrument", "backdoor", "did")
            ):
                score += 5
            if capability.id == "A-12-FORECAST" and any(
                token in text for token in ("forecast", "predict", "预测", "time series", "时序")
            ):
                score += 5
            if capability.id == "A-13" and any(
                token in text for token in ("organization", "project", "组织", "项目", "churn", "evm")
            ):
                score += 5
            if capability.id == "A-14" and any(
                token in text for token in ("personal", "habit", "learning", "个人", "习惯", "成长")
            ):
                score += 5
            if capability.id == "A-15" and any(
                token in text for token in ("team", "conflict", "productivity", "团队", "冲突", "协作")
            ):
                score += 5
            if capability.id == "A-18" and any(
                token in text for token in ("complex", "emergence", "复杂系统", "涌现", "entropy")
            ):
                score += 5
            if capability.id == "A-22" and any(
                token in text for token in ("network", "传播", "拓扑", "pagerank", "percolation")
            ):
                score += 5
            if capability.id == "A-23" and any(
                token in text for token in ("agent-based", "abm", "schelling", "opinion", "智能体")
            ):
                score += 5

            if request.target_evidence_grade in ("CE-C3", "CE-C4") and capability.max_evidence_grade in ("CE-C3", "CE-C4"):
                score += 1

            if request.data:
                data_keys = set(request.data.keys())
                if capability.id == "A-12-FORECAST" and ("series" in data_keys or "time_series" in data_keys):
                    score += 3
                if capability.id == "A-12-SCM" and {"df", "cause", "effect"}.issubset(data_keys):
                    score += 3
                if capability.id == "A-22" and ({"adjacency", "adjacency_matrix"} & data_keys):
                    score += 6
                if capability.id == "A-18" and "micro_states" in data_keys:
                    score += 3
                if capability.id == "A-23" and "agents" in data_keys:
                    score += 3

            params = request.params if isinstance(request.params, dict) else {}
            if capability.id == "A-22" and str(params.get("analysis", "")).lower() in ("pagerank", "percolation", "sir"):
                score += 3

            score -= self._dependency_penalty(capability)
            deps_sat = self._deps_satisfied_count(capability)

            if score > 0:
                candidates.append(CandidateScore(capability=capability, score=score, deps_satisfied=deps_sat))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.score, item.deps_satisfied, item.capability.id), reverse=True)
        return candidates[0].capability

    def explain(
        self,
        request: MetaAnalysisRequest,
        selected: Optional[CapabilityDescriptor],
        *,
        bridge: LegacyMetaBridge | None = None,
    ) -> str:
        bridge = bridge or self._bridge
        if selected is None:
            return (
                "No direct method match was found after precondition checks; "
                "narrow the task, add structured data (graph, series, causal fields), or clarify domain hints."
            )
        base = (
            f"Selected {selected.id} using task language, data-shape hints, dependency-aware scoring, "
            f"and capability preconditions (max evidence {selected.max_evidence_grade})."
        )
        if bridge:
            blocked = [d for d in selected.dependencies if not bridge.status(d).available]
            if blocked:
                missing = ", ".join(blocked)
                base += (
                    f" Dependencies currently unavailable: {missing}; "
                    f"bridge execution will be degraded until restored."
                )
        return base

    def assumptions(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if selected is None:
            return [
                "Task requires manual review before formal methodology execution.",
                "Confirm data shape matches the intended analysis (graph adjacency, series, causal columns, etc.).",
            ]
        return [
            "Task statement and available fields are specific enough for high-level method routing.",
            "Data adequacy and identification claims remain subject to bridge-level validation.",
        ]
