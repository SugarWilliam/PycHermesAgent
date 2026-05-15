"""
网络科学适配器组 (源自 V4.5.0-GA, 合入 V4.3.1-GA)
A-22: 网络鲁棒性、级联失效、渗流相变
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("metamodel.adapters.network")


class NetworkScienceAdapter:
    """A-22: 网络科学 — 级联失效、渗流、传播动力学

    方法：
      1. 渗流相变（Percolation）— 网络连通性的临界阈值
      2. 级联失效（Cascading Failure）— 负载重分配模型
      3. PageRank中心性 — 节点影响力排名
      4. SIR网络传播 — 超越均场的接触网络模型

    理论来源：
      Barabasi & Albert (1999) "Emergence of scaling in random networks"
      Watts (2002) "A simple model of global cascades on random networks"
      Pastor-Satorras & Vespignani (2001) "Epidemic spreading in scale-free networks"
    """
    adapter_id = "A-22-NETWORK"
    version = "4.5.0"
    disciplines = ["Network Science", "Epidemiology", "Finance", "Infrastructure"]
    theories = [
        "Percolation Theory (Broadbent & Hammersley 1957)",
        "Cascading Failure (Motter & Lai 2002)",
        "Scale-Free Networks (Barabasi-Albert 1999)",
    ]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "percolation")
        if analysis_type == "percolation":
            return self._percolation(data, params)
        elif analysis_type == "cascade":
            return self._cascading_failure(data, params)
        elif analysis_type == "pagerank":
            return self._pagerank(data, params)
        elif analysis_type == "sir_network":
            return self._sir_network(data, params)
        else:
            return {"error": f"Unknown: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    def _percolation(self, data, params):
        """渗流相变：随机删除节点/边，检测连通性突变"""
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {"error": "Need adjacency matrix", "validated": False, "adapter_id": self.adapter_id}

        n = adjacency.shape[0]
        n_removals = int(params.get("n_removals", min(n - 1, 50)))
        n_trials = int(params.get("n_trials", 100))

        # Track largest connected component size vs fraction removed
        fractions = np.linspace(0, 0.8, n_removals)
        gcc_sizes = []

        np.random.seed(42)
        for f in fractions:
            sizes = []
            for _ in range(n_trials):
                # Remove fraction f of nodes
                keep = np.random.random(n) > f
                if np.sum(keep) == 0:
                    sizes.append(0)
                    continue
                sub_adj = adjacency[np.ix_(keep, keep)]
                gcc = self._largest_component_size(sub_adj)
                sizes.append(gcc / np.sum(keep))
            gcc_sizes.append(np.mean(sizes))

        gcc_sizes = np.array(gcc_sizes)

        # Find critical threshold: where GCC drops below 50%
        critical_idx = np.where(gcc_sizes < 0.5)[0]
        fc = fractions[critical_idx[0]] if len(critical_idx) > 0 else 1.0

        # Phase: continuous vs discontinuous
        # Check if drop is sharp (discontinuous, 1st order) or gradual
        if len(gcc_sizes) > 5:
            max_drop = np.max(np.abs(np.diff(gcc_sizes)))
            is_discontinuous = max_drop > 0.3
        else:
            is_discontinuous = False

        return {
            "analysis": "percolation",
            "causal_grade": "C1",
            "causal_note": "Percolation threshold is an emergent property — individual node removals are random, but collective connectivity undergoes sharp phase transition",
            "network_size": n,
            "critical_threshold_fc": round(float(fc), 4),
            "percolation_type": "DISCONTINUOUS (1st order)" if is_discontinuous else "CONTINUOUS (2nd order)",
            "gcc_at_10pct_removal": round(float(gcc_sizes[int(len(fractions)*0.1)]) if len(gcc_sizes) > int(len(fractions)*0.1) else 1.0, 4),
            "gcc_at_50pct_removal": round(float(gcc_sizes[int(len(fractions)*0.5)]) if len(gcc_sizes) > int(len(fractions)*0.5) else 0, 4),
            "robustness": "ROBUST" if fc > 0.5 else "FRAGILE",
            "interpretation": (
                f"Network {'fragments abruptly' if is_discontinuous else 'gradually loses connectivity'} "
                f"when {fc*100:.0f}% of nodes removed. "
                f"{'Scale-free topology provides robustness against random failure' if fc > 0.5 else 'Network vulnerable to random failures — consider redundancy'}"
            ),
            "theory_ref": "Broadbent & Hammersley 1957, Cohen et al. 2000",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _largest_component_size(self, adj):
        """BFS找到最大连通分量"""
        n = adj.shape[0]
        visited = np.zeros(n, dtype=bool)
        max_size = 0
        for i in range(n):
            if not visited[i]:
                size = 0
                stack = [i]
                visited[i] = True
                while stack:
                    node = stack.pop()
                    size += 1
                    neighbors = np.where(adj[node] > 0)[0]
                    for nb in neighbors:
                        if not visited[nb]:
                            visited[nb] = True
                            stack.append(nb)
                max_size = max(max_size, size)
        return max_size

    def _cascading_failure(self, data, params):
        """级联失效：Motter-Lai模型"""
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {"error": "Need adjacency matrix", "validated": False, "adapter_id": self.adapter_id}

        n = adjacency.shape[0]
        capacity_factor = float(params.get("capacity_factor", 1.5))  # Capacity = load * factor

        # Initial load = betweenness centrality (approximate by degree)
        degree = np.sum(adjacency > 0, axis=1)
        load = degree.astype(float)
        capacity = load * capacity_factor

        # Initial attack: remove highest-degree node
        initial_failures = [int(np.argmax(degree))]
        failed = set(initial_failures)

        # Redistribute load and cascade
        round_num = 0
        cascade_sizes = [len(failed)]

        while True:
            round_num += 1
            new_failures = set()

            # Recalculate loads on remaining network
            remaining = [i for i in range(n) if i not in failed]
            if len(remaining) < 2:
                break

            sub_adj = adjacency[np.ix_(remaining, remaining)]
            sub_degree = np.sum(sub_adj > 0, axis=1)

            # New load proportional to degree in reduced network
            total_degree = np.sum(sub_degree)
            if total_degree == 0:
                break

            for idx, node in enumerate(remaining):
                new_load = sub_degree[idx]
                if new_load > capacity[node]:
                    new_failures.add(node)

            if len(new_failures) == 0:
                break

            failed.update(new_failures)
            cascade_sizes.append(len(failed))

            if round_num > n:
                break

        total_cascade = len(failed)
        cascade_ratio = total_cascade / n

        return {
            "analysis": "cascading_failure",
            "causal_grade": "C1",
            "causal_note": "Cascade is an emergent phenomenon — single node failure triggers disproportionate system collapse via load redistribution",
            "initial_attack_nodes": initial_failures,
            "capacity_factor": capacity_factor,
            "cascade_rounds": round_num,
            "total_failed": total_cascade,
            "cascade_ratio": round(float(cascade_ratio), 4),
            "system_survives": cascade_ratio < 0.5,
            "interpretation": (
                f"GLOBAL CASCADE: {total_cascade}/{n} nodes failed ({cascade_ratio*100:.1f}%)"
                if cascade_ratio > 0.5 else
                f"LOCALIZED FAILURE: {total_cascade}/{n} nodes failed — system resilient"
            ),
            "recommendation": (
                "CRITICAL: Network prone to systemic cascade. Increase capacity factor or add redundancy paths."
                if cascade_ratio > 0.5 else
                "Acceptable resilience. Monitor highest-betweenness nodes as attack vulnerability."
            ),
            "theory_ref": "Motter & Lai 2002, Watts 2002",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _pagerank(self, data, params):
        """PageRank中心性"""
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {"error": "Need adjacency matrix", "validated": False, "adapter_id": self.adapter_id}

        n = adjacency.shape[0]
        damping = float(params.get("damping", 0.85))
        tol = float(params.get("tolerance", 1e-6))

        # Normalize columns
        out_degree = np.sum(adjacency, axis=0)
        M = np.divide(adjacency, out_degree, out=np.zeros_like(adjacency, dtype=float), where=out_degree > 0)

        # Power iteration
        pr = np.ones(n) / n
        for _ in range(1000):
            new_pr = (1 - damping) / n + damping * M @ pr
            if np.linalg.norm(new_pr - pr, 1) < tol:
                break
            pr = new_pr

        # Top nodes
        top_indices = np.argsort(pr)[::-1][:5]
        top_nodes = [{"node": int(i), "pagerank": round(float(pr[i]), 6)} for i in top_indices]

        # Gini coefficient of PageRank distribution
        gini = self._gini_coefficient(pr)

        return {
            "analysis": "pagerank",
            "causal_grade": "C1",
            "causal_note": "PageRank measures influence but not causal impact of removing a node",
            "n_nodes": n,
            "top_influencers": top_nodes,
            "gini_coefficient": round(float(gini), 4),
            "network_centrality": "CONCENTRATED" if gini > 0.5 else "DISTRIBUTED",
            "interpretation": f"Influence {'highly concentrated in few hubs' if gini > 0.5 else 'relatively distributed'}. Top node: {top_nodes[0]['node']} (PR={top_nodes[0]['pagerank']:.4f})",
            "theory_ref": "Page et al. 1999, Brin & Page 1998",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _gini_coefficient(self, x):
        """计算Gini系数"""
        x = np.sort(x)
        n = len(x)
        cumsum = np.cumsum(x)
        return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0

    def _sir_network(self, data, params):
        """网络上的SIR传播"""
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2:
            return {"error": "Need adjacency matrix", "validated": False, "adapter_id": self.adapter_id}

        n = adjacency.shape[0]
        beta = float(params.get("beta", 0.3))
        gamma = float(params.get("gamma", 0.1))
        n_steps = int(params.get("n_steps", 100))
        n_trials = int(params.get("n_trials", 50))

        np.random.seed(42)
        peak_infections = []
        final_attack_ratios = []

        for _ in range(n_trials):
            S = np.ones(n)
            I = np.zeros(n)
            R = np.zeros(n)

            # Random initial seed
            patient_zero = np.random.randint(n)
            S[patient_zero] = 0
            I[patient_zero] = 1

            infections_over_time = []

            for _ in range(n_steps):
                new_infections = np.zeros(n)
                new_recoveries = np.zeros(n)

                infected_nodes = np.where(I == 1)[0]
                for node in infected_nodes:
                    # Try to infect neighbors
                    neighbors = np.where(adjacency[node] > 0)[0]
                    for nb in neighbors:
                        if S[nb] == 1 and np.random.random() < beta:
                            new_infections[nb] = 1
                    # Recovery
                    if np.random.random() < gamma:
                        new_recoveries[node] = 1

                S = S * (1 - new_infections)
                I = I * (1 - new_recoveries) + new_infections
                R = R + new_recoveries

                infections_over_time.append(np.sum(I))

            peak_infections.append(np.max(infections_over_time))
            final_attack_ratios.append(np.sum(R) / n)

        # Epidemic threshold: compare to 1/lambda_max where lambda_max is largest eigenvalue
        try:
            eigenvalues = np.linalg.eigvals(adjacency)
            lambda_max = np.max(np.real(eigenvalues))
            theoretical_threshold = 1 / lambda_max if lambda_max > 0 else float("inf")
            above_threshold = beta / gamma > theoretical_threshold
        except Exception:
            lambda_max = None
            theoretical_threshold = None
            above_threshold = None

        return {
            "analysis": "sir_network",
            "causal_grade": "C1",
            "causal_note": "Network structure fundamentally alters epidemic dynamics — scale-free networks have vanishing epidemic threshold",
            "network_size": n,
            "beta": beta,
            "gamma": gamma,
            "r0_effective": round(float(beta / gamma), 4),
            "theoretical_threshold": round(float(theoretical_threshold), 4) if theoretical_threshold else None,
            "lambda_max_adjacency": round(float(lambda_max), 4) if lambda_max else None,
            "above_threshold": above_threshold,
            "peak_infection_mean": round(float(np.mean(peak_infections)), 4),
            "peak_infection_pct": round(float(np.mean(peak_infections) / n * 100), 2),
            "final_attack_ratio": round(float(np.mean(final_attack_ratios)), 4),
            "interpretation": (
                f"EPIDEMIC SPREADS: avg {np.mean(final_attack_ratios)*100:.1f}% infected"
                if (above_threshold or above_threshold is None and np.mean(final_attack_ratios) > 0.1) else
                f"CONTAINED: avg {np.mean(final_attack_ratios)*100:.1f}% infected"
            ),
            "theory_ref": "Pastor-Satorras & Vespignani 2001, Newman 2002",
            "validated": True,
            "adapter_id": self.adapter_id,
        }
