"""PageRank engine migrated from legacy network science adapter."""

from __future__ import annotations

from typing import Dict

import numpy as np


class PageRankEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {
                "success": False,
                "validated": False,
                "method": "PageRank",
                "errors": ["Need adjacency_matrix"],
            }

        n = adjacency.shape[0]
        damping = float(params.get("damping", 0.85))
        tol = float(params.get("tolerance", 1e-6))
        out_degree = np.sum(adjacency, axis=0)
        transition = np.divide(adjacency, out_degree, out=np.zeros_like(adjacency, dtype=float), where=out_degree > 0)
        pr = np.ones(n) / n
        for _ in range(1000):
            updated = (1 - damping) / n + damping * transition @ pr
            if np.linalg.norm(updated - pr, 1) < tol:
                pr = updated
                break
            pr = updated
        top_indices = np.argsort(pr)[::-1][:5]
        top_nodes = [{"node": int(i), "pagerank": float(pr[i])} for i in top_indices]
        return {
            "success": True,
            "validated": True,
            "method": "PageRank",
            "evidence_level": "C1",
            "top_influencers": top_nodes,
            "scores": pr.tolist(),
        }
