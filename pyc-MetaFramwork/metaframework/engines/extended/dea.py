"""DEA efficiency frontier engine."""

from __future__ import annotations

from typing import Dict

import numpy as np
from scipy.optimize import linprog


class DEAEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        teams = data.get("teams")
        if teams is None or len(teams) < 3:
            return {
                "success": False,
                "validated": False,
                "method": "DEA",
                "errors": ["DEA requires >=3 teams with inputs and outputs"],
            }

        inputs = np.array([team["inputs"] for team in teams], dtype=float)
        outputs = np.array([team["outputs"] for team in teams], dtype=float)
        n_teams = len(teams)
        n_inputs = inputs.shape[1]
        n_outputs = outputs.shape[1]
        efficiencies = []

        for i in range(n_teams):
            c = np.zeros(n_teams + 1)
            c[0] = 1.0
            A_ub = []
            b_ub = []
            for k in range(n_inputs):
                row = np.zeros(n_teams + 1)
                row[0] = -inputs[i, k]
                row[1:] = inputs[:, k]
                A_ub.append(row)
                b_ub.append(0.0)
            for m in range(n_outputs):
                row = np.zeros(n_teams + 1)
                row[1:] = -outputs[:, m]
                A_ub.append(row)
                b_ub.append(-outputs[i, m])
            res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub), bounds=[(0, None)] * (n_teams + 1), method="highs")
            efficiencies.append(float(res.x[0]) if res.success else 1.0)

        min_eff_idx = int(np.argmin(efficiencies))
        peers = [idx for idx, eff in enumerate(efficiencies) if eff >= 0.99 and idx != min_eff_idx]

        return {
            "success": True,
            "validated": True,
            "method": "DEA",
            "evidence_level": "C1",
            "team_efficiencies": [
                {"team": i, "efficiency": round(float(e), 4), "frontier": bool(e >= 0.99)}
                for i, e in enumerate(efficiencies)
            ],
            "mean_efficiency": round(float(np.mean(efficiencies)), 4),
            "most_inefficient_team": min_eff_idx,
            "peer_benchmarks": peers[:3],
            "warnings": ["DEA gives relative efficiency against an observed frontier, not causal impact"],
        }
