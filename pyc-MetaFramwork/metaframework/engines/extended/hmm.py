"""Simplified 3-state HMM stage detection engine."""

from __future__ import annotations

from typing import Dict

import numpy as np
from scipy.stats import beta as beta_dist


class HabitHMMEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        compliance = np.asarray(data.get("compliance", []), dtype=float)
        if len(compliance) < 10:
            return {
                "success": False,
                "validated": False,
                "method": "HabitHMM",
                "errors": ["Need >=10 observations for HMM stage detection"],
            }

        comp_norm = np.clip(compliance / 100.0 if np.max(compliance) > 1.5 else compliance, 0.01, 0.99)
        means = [
            np.percentile(comp_norm, 25),
            np.percentile(comp_norm, 50),
            np.percentile(comp_norm, 75),
        ]
        thresholds = [means[0] + (means[1] - means[0]) / 2, means[1] + (means[2] - means[1]) / 2]
        states = np.digitize(comp_norm, thresholds)

        for _ in range(int(params.get("n_iter", 40))):
            state_params = []
            for state in range(3):
                mask = states == state
                if np.sum(mask) > 0:
                    mu = float(np.mean(comp_norm[mask]))
                    var = float(np.var(comp_norm[mask])) if np.var(comp_norm[mask]) > 0 else 0.01
                    mu_clipped = float(np.clip(mu, 0.01, 0.99))
                    var_max = max(mu_clipped * (1 - mu_clipped) - 0.01, 1e-6)
                    var = min(max(var, 1e-6), var_max)
                    common = mu_clipped * (1 - mu_clipped) / var - 1
                    a = float(np.clip(mu_clipped * common, 0.5, 50))
                    b = float(np.clip((1 - mu_clipped) * common, 0.5, 50))
                    state_params.append((a, b))
                else:
                    state_params.append((1.0, 1.0))

            new_states = np.zeros_like(states)
            for idx, value in enumerate(comp_norm):
                likelihoods = [beta_dist.pdf(value, a, b) for a, b in state_params]
                new_states[idx] = int(np.argmax(likelihoods))
            if np.array_equal(states, new_states):
                break
            states = new_states

        state_names = ["struggle", "consolidate", "automatic"]
        current_state = int(states[-1])
        relapse_points = []
        for idx in range(1, len(states)):
            if states[idx] < states[idx - 1]:
                relapse_points.append(idx + 1)

        time_in_current = 0
        for idx in range(len(states) - 1, -1, -1):
            if states[idx] == current_state:
                time_in_current += 1
            else:
                break

        return {
            "success": True,
            "validated": True,
            "method": "HabitHMM",
            "evidence_level": "C1",
            "current_stage": state_names[current_state],
            "time_in_current_stage_days": int(time_in_current),
            "stage_distribution": {
                "struggle_pct": round(float(np.mean(states == 0) * 100), 1),
                "consolidate_pct": round(float(np.mean(states == 1) * 100), 1),
                "automatic_pct": round(float(np.mean(states == 2) * 100), 1),
            },
            "relapse_detected": bool(relapse_points),
            "relapse_days": relapse_points[:5],
            "warnings": ["HMM stage detection is descriptive and does not identify causal mechanisms"],
        }
