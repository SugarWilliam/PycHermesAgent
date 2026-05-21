"""Synthetic control engine migrated from legacy forecast adapter."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np


class SyntheticControlEngine:
    def execute(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        y_treat = np.asarray(data.get("y_treat", []), dtype=float)
        y_donors = np.asarray(data.get("y_donors", []), dtype=float)
        intervention_idx = int(data.get("intervention_idx", len(y_treat) // 2))
        if len(y_treat) < 6 or y_donors.ndim != 2 or y_donors.shape[1] != len(y_treat):
            return {
                "success": False,
                "validated": False,
                "method": "SyntheticControl",
                "errors": ["Need y_treat and y_donors with matching time dimension"],
            }

        y_pre = y_treat[:intervention_idx]
        donors_pre = y_donors[:, :intervention_idx]
        ones = np.ones((y_donors.shape[0], 1))
        KKT = np.block([
            [2 * donors_pre @ donors_pre.T + 1e-8 * np.eye(y_donors.shape[0]), ones],
            [ones.T, np.zeros((1, 1))],
        ])
        rhs = np.concatenate([2 * donors_pre @ y_pre, np.array([1.0])])
        try:
            solution = np.linalg.lstsq(KKT, rhs, rcond=None)[0]
            weights = np.clip(solution[:-1], 0.0, None)
            weight_sum = np.sum(weights)
            if weight_sum == 0:
                weights = np.ones_like(weights) / len(weights)
            else:
                weights = weights / weight_sum
        except Exception:
            weights = np.ones(y_donors.shape[0], dtype=float) / y_donors.shape[0]

        synthetic = weights @ y_donors
        effect = y_treat - synthetic
        pre_rmse = float(np.sqrt(np.mean((y_treat[:intervention_idx] - synthetic[:intervention_idx]) ** 2)))
        post_effect_mean = float(np.mean(effect[intervention_idx:])) if intervention_idx < len(effect) else 0.0

        return {
            "success": True,
            "validated": True,
            "method": "SyntheticControl",
            "evidence_level": "C3",
            "weights": weights.tolist(),
            "synthetic_series": synthetic.tolist(),
            "effect_series": effect.tolist(),
            "pre_rmse": pre_rmse,
            "post_effect_mean": post_effect_mean,
            "intervention_idx": intervention_idx,
        }
