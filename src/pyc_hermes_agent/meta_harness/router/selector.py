"""Simple method selection for the minimum viable harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pyc_hermes_agent.contracts import CapabilityDescriptor, MetaAnalysisRequest
from pyc_hermes_agent.meta_harness.registry.catalog import CapabilityRegistry


@dataclass(slots=True)
class CandidateScore:
    capability: CapabilityDescriptor
    score: int


class MethodSelector:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def select(self, request: MetaAnalysisRequest) -> Optional[CapabilityDescriptor]:
        text = request.problem_statement.lower()
        candidates: list[CandidateScore] = []

        for capability in self.registry.all():
            score = 0

            if capability.id == "A-12-SCM" and any(token in text for token in ("causal", "因果", "instrument", "backdoor", "did")):
                score += 5
            if capability.id == "A-12-FORECAST" and any(token in text for token in ("forecast", "predict", "预测", "time series", "时序")):
                score += 5
            if capability.id == "A-13" and any(token in text for token in ("organization", "project", "组织", "项目", "churn", "evm")):
                score += 5
            if capability.id == "A-14" and any(token in text for token in ("personal", "habit", "learning", "个人", "习惯", "成长")):
                score += 5
            if capability.id == "A-15" and any(token in text for token in ("team", "conflict", "productivity", "团队", "冲突", "协作")):
                score += 5
            if capability.id == "A-18" and any(token in text for token in ("complex", "emergence", "复杂系统", "涌现", "entropy")):
                score += 5
            if capability.id == "A-22" and any(token in text for token in ("network", "传播", "拓扑", "pagerank", "percolation")):
                score += 5
            if capability.id == "A-23" and any(token in text for token in ("agent-based", "abm", "schelling", "opinion", "智能体")):
                score += 5

            if request.target_evidence_grade in ("CE-C3", "CE-C4") and capability.max_evidence_grade in ("CE-C3", "CE-C4"):
                score += 1

            if request.data:
                data_keys = set(request.data.keys())
                if capability.id == "A-12-FORECAST" and "series" in data_keys:
                    score += 2
                if capability.id == "A-12-SCM" and {"df", "cause", "effect"}.issubset(data_keys):
                    score += 2
                if capability.id == "A-22" and ({"adjacency", "adjacency_matrix"} & data_keys):
                    score += 2
                if capability.id == "A-18" and "micro_states" in data_keys:
                    score += 2

            if score > 0:
                candidates.append(CandidateScore(capability=capability, score=score))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[0].capability

    def explain(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> str:
        if selected is None:
            return "No direct method match was found; the request should be reviewed or narrowed before formal analysis."
        return f"Selected {selected.id} based on task language and current minimum-phase routing heuristics."

    def assumptions(self, request: MetaAnalysisRequest, selected: Optional[CapabilityDescriptor]) -> list[str]:
        if selected is None:
            return ["Task requires manual review before formal methodology execution."]
        return [
            "Task statement is specific enough for high-level method routing.",
            "Detailed data adequacy checks are deferred to later harness phases.",
        ]
