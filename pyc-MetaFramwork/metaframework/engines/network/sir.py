"""Network SIR engine migrated from legacy network science adapter."""

from __future__ import annotations

from typing import Dict

import numpy as np


class SIREngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {
                "success": False,
                "validated": False,
                "method": "NetworkSIR",
                "errors": ["Need adjacency_matrix"],
            }

        n = adjacency.shape[0]
        beta = float(params.get("beta", 0.3))
        gamma = float(params.get("gamma", 0.1))
        n_steps = int(params.get("n_steps", 50))
        n_trials = int(params.get("n_trials", 20))
        rng = np.random.default_rng(int(params.get("seed", 42)))

        peak_infections = []
        final_attack_ratios = []
        for _ in range(n_trials):
            S = np.ones(n)
            I = np.zeros(n)
            R = np.zeros(n)
            patient_zero = int(rng.integers(0, n))
            S[patient_zero] = 0
            I[patient_zero] = 1
            infections_over_time = []
            for _ in range(n_steps):
                new_infections = np.zeros(n)
                new_recoveries = np.zeros(n)
                infected_nodes = np.where(I == 1)[0]
                for node in infected_nodes:
                    neighbors = np.where(adjacency[node] > 0)[0]
                    for nb in neighbors:
                        if S[nb] == 1 and rng.random() < beta:
                            new_infections[nb] = 1
                    if rng.random() < gamma:
                        new_recoveries[node] = 1
                S = S * (1 - new_infections)
                I = I * (1 - new_recoveries) + new_infections
                R = R + new_recoveries
                infections_over_time.append(np.sum(I))
            peak_infections.append(np.max(infections_over_time) if infections_over_time else 0.0)
            final_attack_ratios.append(np.sum(R) / n)

        return {
            "success": True,
            "validated": True,
            "method": "NetworkSIR",
            "evidence_level": "C1",
            "r0_effective": float(beta / gamma) if gamma > 0 else float("inf"),
            "peak_infection_mean": float(np.mean(peak_infections)),
            "final_attack_ratio": float(np.mean(final_attack_ratios)),
            "warnings": ["Network SIR is a simulation-based diffusion model, not strong causal proof"],
        }
