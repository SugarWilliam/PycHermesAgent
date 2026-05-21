"""Capability preconditions for routing (data shape + task hints).

Preconditions gate *selection* only; execution adequacy remains the bridge layer.
"""

from __future__ import annotations

from pyc_hermes_agent.contracts import MetaAnalysisRequest

_GRAPH_ADJ_KEYS = frozenset({"adjacency", "adjacency_matrix", "edges"})


def capability_preconditions_met(capability_id: str, request: MetaAnalysisRequest) -> bool:
    data = request.data if isinstance(request.data, dict) else {}
    keys = {str(k) for k in data.keys()}
    params = request.params if isinstance(request.params, dict) else {}
    text = (request.problem_statement or "").lower()

    if capability_id == "A-22":
        if _GRAPH_ADJ_KEYS & keys:
            return True
        analysis = str(params.get("analysis", "")).lower()
        if analysis in ("pagerank", "percolation", "sir_network", "sir"):
            return bool(_GRAPH_ADJ_KEYS & keys)
        return False

    if capability_id == "A-12-SCM":
        if any(
            token in text
            for token in ("causal", "因果", "instrument", "backdoor", "did", "scm", "结构因果", "identification")
        ):
            return True
        if {"cause", "effect", "df", "treatment", "outcome", "dag", "confounders"} & keys:
            return True
        return False

    if capability_id == "A-12-FORECAST":
        if {"series", "time_series", "timestamps", "values", "history"} & keys:
            return True
        if any(token in text for token in ("forecast", "predict", "预测", "time series", "时序", "arima", "baseline")):
            return True
        return False

    if capability_id == "A-18":
        if {"micro_states", "microstate", "state_space", "states"} & keys:
            return True
        if any(token in text for token in ("complex", "emergence", "复杂系统", "涌现", "entropy")):
            return True
        return False

    if capability_id == "A-23":
        if any(token in text for token in ("agent-based", "abm", "schelling", "opinion", "智能体")):
            return True
        if {"agents", "agent_count", "breeds", "population", "parameters"} & keys:
            return True
        return False

    # NOTE: A-13, A-14, A-15 (org_personal_adapters) are available only in the
    # standalone pyc-MetaFramework project. Their precondition block was removed
    # because those methods are no longer in the default catalog. They may be
    # re-enabled when the bridge supports lazy adapter loading.

    return True
