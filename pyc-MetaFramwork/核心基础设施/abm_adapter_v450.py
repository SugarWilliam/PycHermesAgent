"""
Agent-Based Modeling适配器 (源自 V4.5.0-GA, 合入 V4.3.1-GA)
A-23: 微观Agent交互 -> 宏观涌现模式提取
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger("metamodel.adapters.abm")


class ABMAdapter:
    """A-23: Agent-Based Modeling引擎

    通用ABM框架：定义Agent规则 -> 模拟演化 -> 提取宏观序参量

    内置模型：
      1. Schelling隔离模型 — 微观偏好 -> 宏观隔离涌现
      2. 意见动力学（DeGroot / 有界置信）— 微观交互 -> 极化/共识涌现
      3. 知识扩散 — 微观学习 -> 宏观创新S曲线

    理论来源：
      Epstein & Axtell (1996) "Growing Artificial Societies"
      Schelling (1971) "Dynamic Models of Segregation"
      Hegselmann & Krause (2002) "Opinion Dynamics"
    """
    adapter_id = "A-23-ABM"
    version = "4.5.0"
    disciplines = ["Agent-Based Modeling", "Complex Systems", "Computational Social Science"]
    theories = [
        "Epstein Axtell Sugarscape (1996)",
        "Schelling Segregation (1971)",
        "Bounded Confidence (Hegselmann-Krause 2002)",
    ]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        model_type = params.get("model", "schelling")
        if model_type == "schelling":
            return self._schelling_model(data, params)
        elif model_type == "opinion":
            return self._opinion_dynamics(data, params)
        elif model_type == "knowledge":
            return self._knowledge_diffusion(data, params)
        elif model_type == "custom":
            return self._custom_abm(data, params)
        else:
            return {"error": f"Unknown ABM model: {model_type}", "validated": False, "adapter_id": self.adapter_id}

    def _schelling_model(self, data, params):
        """Schelling隔离模型：微观容忍度 -> 宏观隔离"""
        grid_size = int(params.get("grid_size", 40))
        tolerance = float(params.get("tolerance", 0.3))  # 容忍不同邻居的比例
        n_agents = int(params.get("n_agents", grid_size * grid_size * 0.9))
        n_types = int(params.get("n_types", 2))
        n_steps = int(params.get("n_steps", 100))

        np.random.seed(42)

        # Initialize grid: 0=empty, 1=typeA, 2=typeB
        grid = np.zeros((grid_size, grid_size), dtype=int)
        positions = [(i, j) for i in range(grid_size) for j in range(grid_size)]
        np.random.shuffle(positions)

        for idx, (i, j) in enumerate(positions[:n_agents]):
            grid[i, j] = (idx % n_types) + 1

        segregation_history = []
        unhappy_history = []

        for step in range(n_steps):
            unhappy = []
            for i in range(grid_size):
                for j in range(grid_size):
                    if grid[i, j] == 0:
                        continue
                    # Count neighbors
                    neighbors = []
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            if di == 0 and dj == 0:
                                continue
                            ni, nj = (i + di) % grid_size, (j + dj) % grid_size
                            if grid[ni, nj] > 0:
                                neighbors.append(grid[ni, nj])

                    if len(neighbors) == 0:
                        continue

                    same_type = sum(1 for n in neighbors if n == grid[i, j])
                    fraction_same = same_type / len(neighbors)

                    if fraction_same < tolerance:
                        unhappy.append((i, j))

            unhappy_history.append(len(unhappy))

            # Calculate segregation index (Moran's I simplified)
            segregation = self._segregation_index(grid, n_types)
            segregation_history.append(segregation)

            if len(unhappy) == 0:
                break

            # Move random unhappy agent
            agent = unhappy[np.random.randint(len(unhappy))]
            # Find empty spot
            empty = [(i, j) for i in range(grid_size) for j in range(grid_size) if grid[i, j] == 0]
            if empty:
                new_pos = empty[np.random.randint(len(empty))]
                grid[new_pos[0], new_pos[1]] = grid[agent[0], agent[1]]
                grid[agent[0], agent[1]] = 0

        final_segregation = segregation_history[-1] if segregation_history else 0
        emergence_detected = final_segregation > tolerance + 0.2

        return {
            "model": "schelling_segregation",
            "causal_grade": "C1",
            "causal_note": "Schelling model demonstrates WEAK emergence — segregation is fully derivable from micro rules, just surprising",
            "grid_size": grid_size,
            "tolerance": tolerance,
            "final_segregation_index": round(float(final_segregation), 4),
            "convergence_step": len(segregation_history),
            "emergence_detected": bool(emergence_detected),
            "micro_macro_gap": f"Tolerance={tolerance} but segregation={final_segregation:.3f} — macro pattern exceeds micro intent",
            "interpretation": (
                f"MACRO EMERGENCE: Global segregation={final_segregation:.3f} despite individual tolerance of only {tolerance}"
                if emergence_detected else
                f"No strong emergence: segregation ({final_segregation:.3f}) within tolerance bounds"
            ),
            "theory_ref": "Schelling 1971",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _segregation_index(self, grid, n_types):
        """简化隔离指数"""
        n = grid.shape[0]
        total_same = 0
        total_pairs = 0
        for i in range(n):
            for j in range(n):
                if grid[i, j] == 0:
                    continue
                for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ni, nj = (i+di)%n, (j+dj)%n
                    if grid[ni, nj] > 0:
                        total_pairs += 1
                        if grid[i, j] == grid[ni, nj]:
                            total_same += 1
        return total_same / total_pairs if total_pairs > 0 else 0

    def _opinion_dynamics(self, data, params):
        """有界置信意见动力学：微观交互 -> 极化/共识涌现"""
        n_agents = int(params.get("n_agents", 100))
        n_steps = int(params.get("n_steps", 200))
        epsilon = float(params.get("epsilon", 0.2))  # 置信阈值
        mu = float(params.get("mu", 0.5))  # 收敛速度

        np.random.seed(42)

        # Initialize opinions: bimodal for polarization test
        opinions = np.concatenate([
            np.random.normal(0.3, 0.1, n_agents // 2),
            np.random.normal(0.7, 0.1, n_agents - n_agents // 2)
        ])
        opinions = np.clip(opinions, 0, 1)

        opinion_history = [opinions.copy()]

        for _ in range(n_steps):
            # Random sequential update
            order = np.random.permutation(n_agents)
            for idx in order:
                # Hegselmann-Krause: interact with agents within epsilon
                neighbors = np.abs(opinions - opinions[idx]) < epsilon
                if np.sum(neighbors) > 1:
                    opinions[idx] += mu * (np.mean(opinions[neighbors]) - opinions[idx])

            opinions = np.clip(opinions, 0, 1)
            opinion_history.append(opinions.copy())

        # Detect final phase
        final_opinions = opinion_history[-1]
        from scipy.stats import kurtosis
        kurt = kurtosis(final_opinions)

        if kurt < -1:
            phase = "CONSENSUS"
        elif kurt > 1:
            phase = "POLARIZED"
        elif np.std(final_opinions) < 0.1:
            phase = "CONSENSUS"
        else:
            # Count clusters
            sorted_op = np.sort(final_opinions)
            gaps = np.diff(sorted_op)
            n_clusters = 1 + np.sum(gaps > epsilon)
            phase = "FRAGMENTED" if n_clusters > 2 else "BIPOLAR" if n_clusters == 2 else "CONSENSUS"

        return {
            "model": "opinion_dynamics",
            "causal_grade": "C1",
            "causal_note": "Opinion dynamics shows how local interaction rules produce global patterns — but these patterns are weakly emergent (derivable from rules)",
            "n_agents": n_agents,
            "epsilon": epsilon,
            "final_phase": phase,
            "final_opinion_mean": round(float(np.mean(final_opinions)), 4),
            "final_opinion_std": round(float(np.std(final_opinions)), 4),
            "opinion_clusters": self._count_opinion_clusters(final_opinions, epsilon),
            "interpretation": {
                "CONSENSUS": f"Agents converged to consensus (std={np.std(final_opinions):.3f}) despite initial bimodality",
                "POLARIZED": f"Polarization maintained: {np.std(final_opinions):.3f} spread across agents",
                "FRAGMENTED": "Multiple opinion clusters formed — no dominant narrative",
                "BIPOLAR": "Two stable opinion camps emerged",
            }.get(phase, ""),
            "theory_ref": "Hegselmann & Krause 2002, DeGroot 1974",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _count_opinion_clusters(self, opinions, epsilon):
        """用DBSCAN思想数聚类"""
        sorted_op = np.sort(opinions)
        if len(sorted_op) == 0:
            return 0
        clusters = [[sorted_op[0]]]
        for op in sorted_op[1:]:
            if op - clusters[-1][-1] < epsilon:
                clusters[-1].append(op)
            else:
                clusters.append([op])
        return len(clusters)

    def _knowledge_diffusion(self, data, params):
        """组织知识扩散：微观学习 -> 宏观创新能力涌现"""
        n_agents = int(params.get("n_agents", 50))
        n_steps = int(params.get("n_steps", 100))
        n_knowledge_domains = int(params.get("n_domains", 5))
        learning_rate = float(params.get("learning_rate", 0.1))
        innovation_prob = float(params.get("innovation_prob", 0.05))

        np.random.seed(42)

        # Each agent has knowledge vector [0,1]^n_domains
        knowledge = np.random.random((n_agents, n_knowledge_domains))

        # Network: who talks to whom
        network_density = float(params.get("network_density", 0.2))
        network = np.random.random((n_agents, n_agents)) < network_density
        np.fill_diagonal(network, False)

        # Track macro-level innovation
        avg_knowledge_history = []
        max_knowledge_history = []
        novel_combinations = []

        for step in range(n_steps):
            # Random interaction
            for _ in range(n_agents):
                i = np.random.randint(n_agents)
                neighbors = np.where(network[i])[0]
                if len(neighbors) > 0:
                    j = np.random.choice(neighbors)
                    # Knowledge transfer: agent i learns from j
                    transfer = learning_rate * (knowledge[j] - knowledge[i])
                    knowledge[i] += transfer
                    knowledge[i] = np.clip(knowledge[i], 0, 1)

            # Innovation: random recombination
            if np.random.random() < innovation_prob:
                agent = np.random.randint(n_agents)
                domain_a, domain_b = np.random.choice(n_knowledge_domains, 2, replace=False)
                if knowledge[agent, domain_a] > 0.5 and knowledge[agent, domain_b] > 0.5:
                    # Cross-domain innovation boosts both
                    knowledge[agent] = np.clip(knowledge[agent] * 1.1, 0, 1)
                    novel_combinations.append((step, agent, domain_a, domain_b))

            avg_knowledge_history.append(float(np.mean(knowledge)))
            max_knowledge_history.append(float(np.max(knowledge)))

        # Detect innovation burst (emergence)
        knowledge_growth = np.diff(avg_knowledge_history)
        burst_detected = np.max(knowledge_growth) > 2 * np.mean(knowledge_growth[knowledge_growth > 0])

        # Aggregate S-curve fit (V4.3.1: 本地导入，适配扁平目录结构)
        from complex_systems_adapters import EvolutionaryAdapter
        evo = EvolutionaryAdapter()
        bass_result = evo(data={"cumulative_adoption": np.array(avg_knowledge_history) * n_agents},
                         params={"analysis": "diffusion"})

        return {
            "model": "knowledge_diffusion",
            "causal_grade": "C1",
            "causal_note": "Knowledge diffusion is weakly emergent — innovation rate is derivable from micro learning rules, but timing of breakthroughs is not",
            "n_agents": n_agents,
            "final_avg_knowledge": round(float(avg_knowledge_history[-1]), 4),
            "final_max_knowledge": round(float(max_knowledge_history[-1]), 4),
            "n_innovations": len(novel_combinations),
            "innovation_burst": bool(burst_detected),
            "bass_diffusion_p": bass_result.get("p_innovation"),
            "bass_diffusion_q": bass_result.get("q_imitation"),
            "interpretation": (
                f"KNOWLEDGE EMERGENCE: {len(novel_combinations)} cross-domain innovations, "
                f"{'with innovation burst detected' if burst_detected else 'gradual accumulation'}. "
                f"Diffusion p={bass_result.get('p_innovation', 'N/A'):.4f}, q={bass_result.get('q_imitation', 'N/A'):.4f}"
            ),
            "theory_ref": "Cowan & Jonard 2004, Fleming & Sorenson 2001",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _custom_abm(self, data, params):
        """自定义ABM：用户提供规则函数"""
        init_func = data.get("init_function")
        step_func = data.get("step_function")
        n_steps = int(params.get("n_steps", 100))

        if init_func is None or step_func is None:
            return {"error": "Custom ABM requires init_function and step_function", "validated": False, "adapter_id": self.adapter_id}

        try:
            state = init_func()
            history = [state]
            for _ in range(n_steps):
                state = step_func(state)
                history.append(state)
            return {
                "model": "custom_abm",
                "final_state": state,
                "history_summary": f"Simulated {n_steps} steps",
                "causal_grade": "C1",
                "causal_note": "ABM generates macro patterns from micro rules — emergence is weak (derivable) if rules are deterministic",
                "validated": True,
                "adapter_id": self.adapter_id,
            }
        except Exception as e:
            return {"error": f"Custom ABM failed: {e}", "validated": False, "adapter_id": self.adapter_id}
