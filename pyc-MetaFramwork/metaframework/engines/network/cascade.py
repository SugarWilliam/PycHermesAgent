"""Cascading failure engine."""

from __future__ import annotations

from typing import Dict

import numpy as np


class CascadingFailureEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {
                "success": False,
                "validated": False,
                "method": "Cascade",
                "errors": ["Need adjacency_matrix"],
            }

        n = adjacency.shape[0]
        capacity_factor = float(params.get("capacity_factor", 1.5))
        degree = np.sum(adjacency > 0, axis=1)
        load = degree.astype(float)
        capacity = load * capacity_factor
        initial_failures = [int(np.argmax(degree))]
        failed = set(initial_failures)
        round_num = 0
        cascade_sizes = [len(failed)]

        while True:
            round_num += 1
            new_failures = set()
            remaining = [idx for idx in range(n) if idx not in failed]
            if len(remaining) < 2:
                break
            sub_adj = adjacency[np.ix_(remaining, remaining)]
            sub_degree = np.sum(sub_adj > 0, axis=1)
            total_degree = np.sum(sub_degree)
            if total_degree == 0:
                break
            for local_idx, node in enumerate(remaining):
                if sub_degree[local_idx] > capacity[node]:
                    new_failures.add(node)
            if not new_failures:
                break
            failed.update(new_failures)
            cascade_sizes.append(len(failed))
            if round_num > n:
                break

        total_cascade = len(failed)
        cascade_ratio = total_cascade / n if n > 0 else 0.0
        return {
            "success": True,
            "validated": True,
            "method": "Cascade",
            "evidence_level": "C1",
            "initial_attack_nodes": initial_failures,
            "cascade_rounds": round_num,
            "total_failed": total_cascade,
            "cascade_ratio": round(float(cascade_ratio), 4),
            "system_survives": bool(cascade_ratio < 0.5),
            "warnings": ["Cascade analysis is structural failure simulation, not causal proof"],
        }
