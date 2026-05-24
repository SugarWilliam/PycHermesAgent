"""Method selection with data-shape preconditions and dependency-aware scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest
from pyc_hermes_agent.meta_harness.registry.catalog import CapabilityRegistry
from pyc_hermes_agent.meta_harness.router.policy import (
    MethodRoutingPolicy,
    default_params_bonus,
    routing_pin_method_id,
)
from pyc_hermes_agent.meta_harness.router.preconditions import capability_preconditions_met

if TYPE_CHECKING:
    from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge


@dataclass(slots=True)
class CandidateScore:
    capability: CapabilityDescriptor
    score: int
    deps_satisfied: int


class MethodSelector:
    def __init__(
        self,
        registry: CapabilityRegistry,
        bridge: LegacyMetaBridge | None = None,
        *,
        routing_policy: MethodRoutingPolicy | None = None,
    ) -> None:
        self.registry = registry
        self._bridge = bridge
        self._routing_policy = routing_policy or MethodRoutingPolicy.builtin()

    def _allowed_method_ids(self, request: MetaAnalysisRequest) -> frozenset[str] | None:
        raw = getattr(request, "allowed_methods", None) or []
        filtered = frozenset(str(x).strip() for x in raw if str(x).strip())
        return filtered or None

    def _dependency_penalty(self, capability: CapabilityDescriptor, policy: MethodRoutingPolicy) -> int:
        if self._bridge is None:
            return 0
        missing = sum(1 for dependency in capability.dependencies if not self._bridge.status(dependency).available)
        return missing * policy.dependency_penalty_per_missing

    def _deps_satisfied_count(self, capability: CapabilityDescriptor) -> int:
        if self._bridge is None:
            return len(capability.dependencies)
        return sum(1 for d in capability.dependencies if self._bridge.status(d).available)

    def select(self, request: MetaAnalysisRequest) -> Optional[CapabilityDescriptor]:
        policy = self._routing_policy.with_request_overlay(request)
        text = request.problem_statement.lower()
        allowed = self._allowed_method_ids(request)

        pin_id = routing_pin_method_id(request)
        if pin_id:
            pinned = self.registry.get(pin_id)
            if pinned is not None and capability_preconditions_met(pinned.id, request):
                if allowed is None or pinned.id in allowed:
                    return pinned

        candidates: list[CandidateScore] = []

        for capability in self.registry.all():
            if allowed is not None and capability.id not in allowed:
                continue
            if not capability_preconditions_met(capability.id, request):
                continue

            score = 0
            score += policy.language_bonus(capability.id, text)
            score += policy.evidence_target_bonus(request, capability.max_evidence_grade)

            if isinstance(request.data, dict):
                data_keys = set(request.data.keys())
                score += policy.data_shape_score(capability.id, data_keys)

            params = request.params if isinstance(request.params, dict) else {}
            score += default_params_bonus(capability.id, params)

            score -= self._dependency_penalty(capability, policy)
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
        pin_id = routing_pin_method_id(request)
        if selected is not None and pin_id and selected.id == pin_id:
            return f"Pinned {selected.id} via meta_routing (preconditions satisfied; max evidence {selected.max_evidence_grade})."
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
                base += f" Dependencies currently unavailable: {missing}; bridge execution will be degraded until restored."
        return base

    def assumptions(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if routing_pin_method_id(request) and selected is not None:
            return [
                "Formal method was pinned via meta_routing; confirm this matches governance and task intent.",
                "Data adequacy and identification claims remain subject to bridge-level validation.",
            ]
        if selected is None:
            return [
                "Task requires manual review before formal methodology execution.",
                "Confirm data shape matches the intended analysis (graph adjacency, series, causal columns, etc.).",
            ]
        return [
            "Task statement and available fields are specific enough for high-level method routing.",
            "Data adequacy and identification claims remain subject to bridge-level validation.",
        ]
