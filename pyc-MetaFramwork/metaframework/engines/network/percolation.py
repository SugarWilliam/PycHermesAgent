"""Percolation robustness engine."""

from __future__ import annotations

from typing import Dict

import numpy as np


class PercolationEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {
                "success": False,
                "validated": False,
                "method": "Percolation",
                "errors": ["Need adjacency_matrix"],
            }

        n = adjacency.shape[0]
        n_removals = int(params.get("n_removals", min(n - 1, 30)))
        n_trials = int(params.get("n_trials", 50))
        rng = np.random.default_rng(int(params.get("seed", 42)))
        fractions = np.linspace(0, 0.8, n_removals)
        gcc_sizes = []
        for fraction in fractions:
            sizes = []
            for _ in range(n_trials):
                keep = rng.random(n) > fraction
                if np.sum(keep) == 0:
                    sizes.append(0)
                    continue
                sub_adj = adjacency[np.ix_(keep, keep)]
                sizes.append(self._largest_component_size(sub_adj) / np.sum(keep))
            gcc_sizes.append(np.mean(sizes))
        gcc_sizes = np.array(gcc_sizes)
        critical_idx = np.where(gcc_sizes < 0.5)[0]
        fc = float(fractions[critical_idx[0]]) if len(critical_idx) > 0 else 1.0
        max_drop = float(np.max(np.abs(np.diff(gcc_sizes)))) if len(gcc_sizes) > 5 else 0.0
        is_discontinuous = bool(max_drop > 0.3)

        return {
            "success": True,
            "validated": True,
            "method": "Percolation",
            "evidence_level": "C1",
            "critical_threshold_fc": round(fc, 4),
            "percolation_type": "DISCONTINUOUS" if is_discontinuous else "CONTINUOUS",
            "gcc_curve": [round(float(x), 4) for x in gcc_sizes],
            "warnings": ["Percolation analysis is a robustness characterization, not causal proof"],
        }

    def _largest_component_size(self, adj: np.ndarray) -> int:
        n = adj.shape[0]
        visited = np.zeros(n, dtype=bool)
        max_size = 0
        for idx in range(n):
            if visited[idx]:
                continue
            size = 0
            stack = [idx]
            visited[idx] = True
            while stack:
                node = stack.pop()
                size += 1
                neighbors = np.where(adj[node] > 0)[0]
                for neighbor in neighbors:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        stack.append(neighbor)
            max_size = max(max_size, size)
        return max_size
