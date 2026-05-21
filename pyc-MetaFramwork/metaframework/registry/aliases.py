"""Legacy adapter id aliases for MetaFramework v0.1."""

from __future__ import annotations

from typing import Dict


LEGACY_CAPABILITY_ALIASES: Dict[str, str] = {
    "A-12-SCM": "causal.effect.scm",
    "A-12-SYNTH": "causal.effect.synthetic_control",
    "A-16": "complex.early_warning.csd",
    "A-22": "network.centrality.pagerank",
    "A-22-NETWORK": "network.centrality.pagerank",
    "A-14-PERS-GOAL-LIMIT": "extended.state.kalman_goal",
    "A-14-PERS-HABIT-LIMIT": "extended.state.habit_hmm",
    "A-13-ORG-CHURN-LIMIT": "extended.survival.cox",
    "A-15-TEAM-PROD-LIMIT": "extended.efficiency.dea",
    "A-15-TEAM-SIZE-LIMIT": "extended.queueing.mmc",
}


def resolve_capability_alias(capability_id: str) -> str:
    return LEGACY_CAPABILITY_ALIASES.get(capability_id, capability_id)
