"""Minimal request validation for stable v0.1 capabilities."""

from __future__ import annotations

from typing import Any, Dict, List


_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "stats.rigor.bootstrap_fdr": ["series", "change_indices"],
    "causal.effect.scm": ["df", "cause", "effect"],
    "causal.effect.synthetic_control": ["y_treat", "y_donors", "intervention_idx"],
    "causal.effect.did": ["treat_pre", "treat_post", "control_pre", "control_post"],
    "complex.early_warning.csd": ["series"],
    "complex.transition.hysteresis": ["x_forward", "y_forward", "x_reverse", "y_reverse"],
    "network.centrality.pagerank": ["adjacency_matrix"],
    "network.robustness.percolation": ["adjacency_matrix"],
    "network.failure.cascade": ["adjacency_matrix"],
    "network.diffusion.sir": ["adjacency_matrix"],
    "extended.state.kalman_goal": ["progress_series"],
    "extended.state.habit_hmm": ["compliance"],
    "extended.survival.cox": ["df"],
    "extended.efficiency.dea": ["teams"],
    "extended.queueing.mmc": ["task_arrival_rate", "task_completion_rate"],
    "extended.project.evm": ["planned_value", "earned_value", "actual_cost"],
    "extended.learning.curve": ["trials", "performance"],
}


def validate_request_data(capability_id: str, data: Dict[str, Any]) -> List[str]:
    missing = []
    for field in _REQUIRED_FIELDS.get(capability_id, []):
        if field not in data:
            missing.append(field)
    return missing


def get_required_fields(capability_id: str) -> List[str]:
    return list(_REQUIRED_FIELDS.get(capability_id, []))
