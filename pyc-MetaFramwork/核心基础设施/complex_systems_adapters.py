"""
复杂系统科学完整补齐适配器组 (源自 V4.5.0-GA, 合入 V4.3.1-GA)
A-16: 临界点预警 (Tipping Points / Critical Transitions)
A-17: 自组织临界性 (Self-Organized Criticality)
A-18: 因果涌现量化 (Causal Emergence via Effective Information)
A-19: 信息论因果 (Transfer Entropy)
A-20: 演化动力学 (Evolutionary Adaptive Dynamics)
A-21: 多尺度粗粒化 (Coarse-Graining Multi-scale Bridge)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger("metamodel.adapters.complex_systems")


# ============================================================
# A-16: TIPPING — 临界转变早期预警
# ============================================================
class TippingAdapter:
    """A-16: 临界转变早期预警系统

    方法：
      1. 自相关(AR1)趋势 — Critical Slowing Down (Dakos et al. 2008)
      2. 方差趋势 — 系统对扰动恢复能力减弱
      3. 峰度/偏度变化 — 概率分布变厚尾
      4. 滞回检测 — 多稳态系统的路径依赖

    理论来源：
      Dakos et al. (2008) "Slowing down as an early warning signal"
      Scheffer et al. (2009) "Early-warning signals for critical transitions"
      Lenton et al. (2008) "Tipping elements in the Earth's climate system"
    """
    adapter_id = "A-16-TIPPING"
    version = "4.5.0"
    disciplines = ["Complex Systems", "Climate Science", "Ecology", "Finance"]
    theories = [
        "Critical Slowing Down (Dakos 2008)",
        "Scheffer Critical Transitions (2009)",
        "Hysteresis in Multi-stable Systems",
    ]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "csd")  # csd / hysteresis
        if analysis_type == "csd":
            return self._critical_slowing_down(data, params)
        elif analysis_type == "hysteresis":
            return self._hysteresis_detection(data, params)
        else:
            return {"error": f"Unknown: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    def _critical_slowing_down(self, data, params):
        """检测临界慢化的三个指标：AR1、方差、恢复时间"""
        series = np.asarray(data.get("series", []), dtype=float)
        if len(series) < 50:
            return {"error": "Need >=50 for CSD detection", "validated": False, "adapter_id": self.adapter_id}

        window_size = int(params.get("window_size", max(20, len(series) // 10)))
        step = int(params.get("step", max(5, window_size // 4)))

        ar1_values = []
        variance_values = []
        recovery_times = []
        window_centers = []

        for start in range(0, len(series) - window_size, step):
            end = start + window_size
            window = series[start:end]
            window_centers.append(start + window_size // 2)

            # AR1 coefficient
            y = window[1:]
            x = window[:-1]
            ar1 = np.corrcoef(x, y)[0, 1] if np.std(x) > 0 else 0
            ar1_values.append(ar1)

            # Variance (detrended)
            detrended = window - np.linspace(window[0], window[-1], len(window))
            variance_values.append(np.var(detrended))

            # Recovery time: mean reversion rate
            residuals = y - x * ar1
            recovery_rate = 1 - ar1
            recovery_times.append(1 / max(recovery_rate, 0.01))

        # Trend test: Kendall tau on the indicator series
        from scipy.stats import kendalltau
        tau_ar1, p_ar1 = kendalltau(range(len(ar1_values)), ar1_values)
        tau_var, p_var = kendalltau(range(len(variance_values)), variance_values)

        # Composite early warning score
        scores = []
        if p_ar1 < 0.05 and tau_ar1 > 0:
            scores.append("AR1_UP")
        if p_var < 0.05 and tau_var > 0:
            scores.append("VARIANCE_UP")

        ew_score = len(scores)

        if ew_score >= 2:
            status = "WARNING: Multiple CSD indicators trending — system may be approaching tipping point"
            risk_level = "HIGH"
        elif ew_score == 1:
            status = "CAUTION: One CSD indicator trending — monitor closely"
            risk_level = "MEDIUM"
        else:
            status = "STABLE: No critical slowing down detected"
            risk_level = "LOW"

        # Tipping probability model (logistic on composite)
        if len(ar1_values) >= 2:
            current_ar1 = ar1_values[-1]
            baseline_ar1 = np.mean(ar1_values[:max(1, len(ar1_values)//3)])
            ar1_ratio = current_ar1 / max(baseline_ar1, 0.01)
            tipping_prob = 1 / (1 + np.exp(-5 * (ar1_ratio - 1.5))) * 100
        else:
            tipping_prob = 0.0

        return {
            "analysis": "critical_slowing_down",
            "causal_grade": "C1",
            "causal_note": "CSD is a phenomenological indicator, not a causal mechanism. High AR1 predicts proximity to bifurcation but does not guarantee it",
            "risk_level": risk_level,
            "early_warning_score": ew_score,
            "status": status,
            "indicators": {
                "ar1_trend": {"tau": round(float(tau_ar1), 4), "p_value": round(float(p_ar1), 4),
                              "current": round(float(ar1_values[-1]), 4) if ar1_values else None,
                              "baseline": round(float(np.mean(ar1_values[:max(1, len(ar1_values)//3)])), 4) if ar1_values else None},
                "variance_trend": {"tau": round(float(tau_var), 4), "p_value": round(float(p_var), 4),
                                   "current": round(float(variance_values[-1]), 4) if variance_values else None},
            },
            "tipping_probability_pct": round(float(tipping_prob), 2),
            "interpretation": {
                "HIGH": "Reduce system stress, identify and remove destabilizing feedback loops",
                "MEDIUM": "Increase monitoring frequency, prepare contingency plans",
                "LOW": "No immediate action needed based on CSD indicators",
            }[risk_level],
            "theory_ref": "Dakos et al. 2008, Scheffer et al. 2009",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _hysteresis_detection(self, data, params):
        """检测多稳态系统的滞回环"""
        x_forward = np.asarray(data.get("x_forward", []), dtype=float)
        y_forward = np.asarray(data.get("y_forward", []), dtype=float)
        x_reverse = np.asarray(data.get("x_reverse", []), dtype=float)
        y_reverse = np.asarray(data.get("y_reverse", []), dtype=float)

        if len(x_forward) < 3 or len(x_reverse) < 3:
            return {"error": "Need forward and reverse sweep data", "validated": False, "adapter_id": self.adapter_id}

        # Check if reverse path deviates from forward path
        # Interpolate reverse onto forward x-grid
        y_rev_interp = np.interp(x_forward, x_reverse, y_reverse)
        deviation = y_forward - y_rev_interp
        mean_deviation = np.mean(np.abs(deviation))

        # Normalize by total range
        y_range = np.max(np.concatenate([y_forward, y_reverse])) - np.min(np.concatenate([y_forward, y_reverse]))
        hysteresis_index = mean_deviation / y_range if y_range > 0 else 0

        has_hysteresis = hysteresis_index > 0.1  # Threshold for meaningful hysteresis

        # Area of hysteresis loop (approximate)
        # Close the loop: forward then reverse
        loop_x = np.concatenate([x_forward, x_reverse[::-1]])
        loop_y = np.concatenate([y_forward, y_reverse[::-1]])
        loop_area = 0.5 * np.abs(np.sum(loop_x[:-1] * loop_y[1:] - loop_x[1:] * loop_y[:-1]))

        return {
            "analysis": "hysteresis",
            "causal_grade": "C2",
            "causal_note": "Hysteresis implies multi-stability and path dependence — once crossed, threshold recovery requires different conditions than collapse",
            "has_hysteresis": has_hysteresis,
            "hysteresis_index": round(float(hysteresis_index), 4),
            "loop_area": round(float(loop_area), 4),
            "forward_range": [round(float(np.min(y_forward)), 4), round(float(np.max(y_forward)), 4)],
            "reverse_range": [round(float(np.min(y_reverse)), 4), round(float(np.max(y_reverse)), 4)],
            "interpretation": "System exhibits multi-stability" if has_hysteresis else "No significant hysteresis detected — system likely has single stable state",
            "theory_ref": "Scheffer et al. 2001, Beisner et al. 2003",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


# ============================================================
# A-17: SOC — 自组织临界性检测
# ============================================================
class SOCAdapter:
    """A-17: 自组织临界性检测与模拟

    方法：
      1. 幂律分布拟合（事件大小/频率）
      2. Bak-Tang-Wiesenfeld Sandpile模拟
      3.  avalanche size分布分析

    理论来源：Bak, Tang & Wiesenfeld (1987)
    """
    adapter_id = "A-17-SOC"
    version = "4.5.0"
    disciplines = ["Statistical Physics", "Finance", "Seismology", "Ecology"]
    theories = ["Bak-Tang-Wiesenfeld SOC (1987)", "Power Law Distributions", "Avalanche Dynamics"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "powerlaw")  # powerlaw / sandpile
        if analysis_type == "powerlaw":
            return self._powerlaw_fit(data, params)
        elif analysis_type == "sandpile":
            return self._sandpile_simulation(data, params)
        else:
            return {"error": f"Unknown: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    def _powerlaw_fit(self, data, params):
        """检测事件大小是否服从幂律分布（SOC标志）"""
        event_sizes = np.asarray(data.get("event_sizes", []), dtype=float)
        if len(event_sizes) < 50:
            return {"error": "Need >=50 events for power-law test", "validated": False, "adapter_id": self.adapter_id}

        # Filter positive sizes
        sizes = event_sizes[event_sizes > 0]
        if len(sizes) < 50:
            return {"error": "Need >=50 positive events", "validated": False, "adapter_id": self.adapter_id}

        # MLE for power-law exponent (Clauset, Shalizi, Newman 2009 simplified)
        xmin = np.percentile(sizes, 10)
        sizes_above = sizes[sizes > xmin]  # Strictly greater to avoid division issues
        if len(sizes_above) < 10:
            sizes_above = sizes[sizes >= xmin]
        n = len(sizes_above)
        log_ratios = np.log(sizes_above / xmin)
        log_ratios = log_ratios[np.isfinite(log_ratios) & (log_ratios > 0)]
        alpha = 1 + len(log_ratios) / np.sum(log_ratios) if len(log_ratios) > 0 and np.sum(log_ratios) > 0 else 2.0

        # Kolmogorov-Smirnov vs exponential alternative
        from scipy.stats import kstest, expon
        # Normalize for KS test
        scaled = sizes_above / np.mean(sizes_above)
        ks_stat_pl, ks_p_pl = kstest(scaled, 'powerlaw', args=(alpha,), N=n)

        # Compare with exponential (competing hypothesis)
        ks_stat_exp, ks_p_exp = kstest(scaled, 'expon')

        # Log-likelihood ratio
        ll_pl = n * np.log(alpha - 1) - alpha * np.sum(np.log(sizes_above / xmin)) - n * np.log(xmin)
        ll_exp = n * np.log(1/np.mean(sizes_above)) - np.sum(sizes_above) / np.mean(sizes_above)
        lr = 2 * (ll_pl - ll_exp)

        is_powerlaw = alpha > 1.5 and alpha < 4.0 and ks_p_pl > 0.05

        # Interpretation
        if is_powerlaw:
            interp = f"SOC-like dynamics detected: event sizes follow power law with exponent alpha={alpha:.2f}. System self-organizes to critical state. Extreme events are intrinsic, not anomalies."
        else:
            interp = f"No clear SOC signature: alpha={alpha:.2f}. Events may be driven by external forcing or follow different distribution."

        return {
            "analysis": "powerlaw",
            "causal_grade": "C1",
            "causal_note": "Power-law distribution suggests underlying SOC mechanism, but does not prove it (need spatiotemporal dynamics)",
            "alpha_mle": round(float(alpha), 4),
            "xmin": round(float(xmin), 4),
            "n_above_xmin": n,
            "ks_statistic": round(float(ks_stat_pl), 4),
            "ks_p_value": round(float(ks_p_pl), 4),
            "is_powerlaw": is_powerlaw,
            "log_likelihood_ratio": round(float(lr), 4),
            "interpretation": interp,
            "theory_ref": "Bak-Tang-Wiesenfeld 1987, Clauset-Shalizi-Newman 2009",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _sandpile_simulation(self, data, params):
        """BTW Sandpile模型模拟"""
        grid_size = int(params.get("grid_size", 50))
        n_grains = int(params.get("n_grains", 50000))
        threshold = int(params.get("threshold", 4))

        # 2D sandpile
        grid = np.zeros((grid_size, grid_size), dtype=int)
        avalanche_sizes = []
        avalanche_durations = []

        np.random.seed(42)
        for _ in range(n_grains):
            # Add grain at random position
            x, y = np.random.randint(0, grid_size, 2)
            grid[x, y] += 1

            # Check for avalanche
            if grid[x, y] >= threshold:
                size, duration = self._topple(grid, x, y, grid_size, threshold)
                avalanche_sizes.append(size)
                avalanche_durations.append(duration)

        # Fit power law to avalanche sizes
        sizes = np.array([s for s in avalanche_sizes if s > 0])
        if len(sizes) > 50:
            xmin = np.percentile(sizes, 5)
            above = sizes[sizes >= xmin]
            alpha = 1 + len(above) / np.sum(np.log(above / xmin))
        else:
            alpha = np.nan

        return {
            "analysis": "sandpile",
            "causal_grade": "C1",
            "causal_note": "Sandpile is a generative model of SOC — demonstrates how local rules produce scale-free avalanches",
            "grid_size": grid_size,
            "n_grains_added": n_grains,
            "n_avalanches": len(avalanche_sizes),
            "mean_avalanche_size": round(float(np.mean(avalanche_sizes)), 2) if avalanche_sizes else 0,
            "max_avalanche_size": int(np.max(avalanche_sizes)) if avalanche_sizes else 0,
            "powerlaw_exponent": round(float(alpha), 4) if not np.isnan(alpha) else None,
            "interpretation": f"Sandpile self-organized to critical state after {n_grains} grains. Avalanche sizes follow power law with alpha={alpha:.2f}." if not np.isnan(alpha) else "Insufficient avalanches for power-law fit",
            "theory_ref": "Bak-Tang-Wiesenfeld 1987",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _topple(self, grid, x, y, size, threshold):
        """递归topple，返回avalanche size和duration"""
        size_count = 0
        duration = 0
        to_topple = [(x, y)]
        visited = set()

        while to_topple:
            duration += 1
            next_topple = []
            for tx, ty in to_topple:
                if (tx, ty) in visited:
                    continue
                visited.add((tx, ty))
                if grid[tx, ty] >= threshold:
                    grid[tx, ty] -= 4
                    size_count += 1
                    # Redistribute to neighbors
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nx, ny = tx + dx, ty + dy
                        if 0 <= nx < size and 0 <= ny < size:
                            grid[nx, ny] += 1
                            if grid[nx, ny] >= threshold and (nx, ny) not in visited:
                                next_topple.append((nx, ny))
            to_topple = next_topple

        return size_count, duration


# ============================================================
# A-18: CAUSAL_EMERGENCE — 因果涌现量化
# ============================================================
class CausalEmergenceAdapter:
    """A-18: 因果涌现量化（Effective Information方法）

    核心思想：如果宏观尺度的有效信息 EI_macro > EI_micro，
    则发生了因果涌现（Hoel et al. 2013, Rosas et al. 2020）

    EI = cause_information * effect_information
       = (统一性) * (确定性)
       = (1 - 分散度) * (1 - 噪声度)
    """
    adapter_id = "A-18-CAUSAL-EMERGENCE"
    version = "4.5.0"
    disciplines = ["Complex Systems", "Information Theory", "Philosophy of Mind"]
    theories = ["Effective Information (Hoel 2013)", "Causal Emergence (Rosas 2020)", "Integrated Information Theory (Tononi)"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        micro_states = np.asarray(data.get("micro_states", []), dtype=int)
        macro_map = data.get("macro_map", None)  # function or array mapping micro->macro

        if len(micro_states) < 100:
            return {"error": "Need >=100 micro states", "validated": False, "adapter_id": self.adapter_id}

        # Compute micro-scale transition matrix
        micro_ei = self._compute_ei(micro_states)

        # Compute macro-scale EI
        if macro_map is not None and callable(macro_map):
            macro_states = macro_map(micro_states)
        elif macro_map is not None:
            macro_states = np.asarray(macro_map, dtype=int)
        else:
            # Default: coarse-grain by binning
            n_bins = int(params.get("n_macro_bins", max(2, len(np.unique(micro_states)) // 10)))
            macro_states = np.digitize(micro_states, np.percentile(micro_states, np.linspace(0, 100, n_bins+1)[1:-1]))

        macro_ei = self._compute_ei(macro_states)

        # Causal emergence measure
        emergence = macro_ei - micro_ei
        emergence_ratio = macro_ei / micro_ei if micro_ei > 0 else float("inf")

        has_emergence = emergence > 0 and emergence_ratio > 1.1

        return {
            "causal_grade": "C1",
            "causal_note": "EI quantifies causal structure at each scale. Emergence > 0 suggests macro scale has more causal power than micro — but this is scale-relative, not absolute causal claim",
            "micro_ei": round(float(micro_ei), 6),
            "macro_ei": round(float(macro_ei), 6),
            "emergence": round(float(emergence), 6),
            "emergence_ratio": round(float(emergence_ratio), 4),
            "has_causal_emergence": has_emergence,
            "interpretation": (
                f"CAUSAL EMERGENCE DETECTED: Macro EI ({macro_ei:.4f}) > Micro EI ({micro_ei:.4f}). "
                f"The macro scale has {emergence_ratio:.2f}x more causal structure. "
                f"This means macro-level descriptions capture causation lost in micro-level noise."
                if has_emergence else
                f"No causal emergence: Macro EI ({macro_ei:.4f}) <= Micro EI ({micro_ei:.4f}). "
                f"System is reductionistically describable at micro scale."
            ),
            "theory_ref": "Hoel et al. 2013, Rosas et al. 2020",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _compute_ei(self, states):
        """计算有效信息 EI = cause_info * effect_info

        支持一维标量状态和多维向量状态输入。
        多维输入时，每个状态向量被映射为唯一的标量标识。
        """
        states_arr = np.asarray(states)

        # Handle multi-dimensional states (e.g., each state is a vector)
        if states_arr.ndim > 1:
            # Map each state vector to a unique scalar via hashable tuple
            state_tuples = [tuple(row) for row in states_arr]
            unique_tuples = sorted(set(state_tuples))
            tuple_to_id = {t: i for i, t in enumerate(unique_tuples)}
            mapped = np.array([tuple_to_id[t] for t in state_tuples])
        else:
            # Scalar states: use np.unique directly
            unique = np.unique(states_arr)
            n = len(unique)
            if n < 2:
                return 0.0
            state_map = {s: i for i, s in enumerate(unique)}
            mapped = np.array([state_map[s] for s in states_arr])

        n = len(np.unique(mapped))
        if n < 2:
            return 0.0

        # Count transitions
        trans = np.zeros((n, n))
        for i in range(len(mapped) - 1):
            trans[mapped[i], mapped[i+1]] += 1

        # Normalize to probability
        row_sums = trans.sum(axis=1, keepdims=True)
        trans_prob = np.divide(trans, row_sums, out=np.zeros_like(trans), where=row_sums > 0)

        # Cause information: 1 - entropy of initial distribution (uniformity)
        init_dist = row_sums.flatten() / np.sum(row_sums)
        cause_info = 1.0 + np.sum(init_dist * np.log(init_dist + 1e-10)) / np.log(n) if n > 1 else 0
        cause_info = max(0, min(1, cause_info))

        # Effect information: average determinism of transitions
        effect_info = 0.0
        for i in range(n):
            if row_sums[i] > 0:
                p = trans_prob[i]
                p = p[p > 0]
                if len(p) > 0:
                    determinism = 1.0 + np.sum(p * np.log(p)) / np.log(len(p)) if len(p) > 1 else 1.0
                    determinism = max(0, min(1, determinism))
                    effect_info += init_dist[i] * determinism

        return cause_info * effect_info


# ============================================================
# A-19: TRANSFER_ENTROPY — 信息论因果方向
# ============================================================
class TransferEntropyAdapter:
    """A-19: 传递熵（Transfer Entropy）方向性因果推断

    TE(X->Y) = I(Y_t : X_{t-1} | Y_{t-1})
    检测信息从X到Y的定向流动，控制Y的自相关后

    理论来源：Schreiber (2000) "Measuring information transfer"
    """
    adapter_id = "A-19-TRANSFER-ENTROPY"
    version = "4.5.0"
    disciplines = ["Information Theory", "Neuroscience", "Finance", "Climate"]
    theories = ["Transfer Entropy (Schreiber 2000)", "Conditional Mutual Information"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        x = np.asarray(data.get("x", []), dtype=float)
        y = np.asarray(data.get("y", []), dtype=float)

        if len(x) < 100 or len(y) < 100:
            return {"error": "Need >=100 points for TE", "validated": False, "adapter_id": self.adapter_id}

        # Discretize
        n_bins = int(params.get("n_bins", min(20, len(x) // 20)))
        x_d = self._discretize(x, n_bins)
        y_d = self._discretize(y, n_bins)

        # Compute TE(X->Y) and TE(Y->X)
        te_xy = self._transfer_entropy(x_d, y_d, n_bins)
        te_yx = self._transfer_entropy(y_d, x_d, n_bins)

        # Significance: permutation test
        n_perm = int(params.get("n_permutations", 100))
        te_xy_null = []
        for _ in range(n_perm):
            x_shuffled = np.random.permutation(x_d)
            te_xy_null.append(self._transfer_entropy(x_shuffled, y_d, n_bins))

        p_value = np.mean(np.array(te_xy_null) >= te_xy)
        significant = p_value < 0.05

        # Net information flow
        net_flow = te_xy - te_yx

        direction = "X->Y" if net_flow > 0.02 else "Y->X" if net_flow < -0.02 else "BIDIRECTIONAL/NO_CLEAR_DIRECTION"

        return {
            "causal_grade": "C1",
            "causal_note": "Transfer entropy detects directed information flow, not causal intervention. Correlated noise sources can mimic TE",
            "te_x_to_y": round(float(te_xy), 6),
            "te_y_to_x": round(float(te_yx), 6),
            "net_flow": round(float(net_flow), 6),
            "direction": direction,
            "p_value": round(float(p_value), 4),
            "significant": significant,
            "interpretation": (
                f"Significant information flow {direction} (TE={te_xy:.4f}, p={p_value:.4f})"
                if significant else
                f"No significant directed information flow (p={p_value:.4f})"
            ),
            "theory_ref": "Schreiber 2000",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _discretize(self, x, n_bins):
        """等频离散化"""
        bins = np.percentile(x, np.linspace(0, 100, n_bins + 1))
        bins[-1] += 1e-6  # Ensure max falls in last bin
        return np.digitize(x, bins[1:]) - 1

    def _transfer_entropy(self, x, y, n_bins):
        """TE(X->Y) = sum p(y_t, y_{t-1}, x_{t-1}) log[p(y_t|y_{t-1},x_{t-1})/p(y_t|y_{t-1})]"""
        n = len(x)
        # y_t, y_{t-1}, x_{t-1}
        y_t = y[1:]
        y_lag = y[:-1]
        x_lag = x[:-1]

        # Count joint
        joint_counts = {}
        y_y_counts = {}
        y_lag_counts = {}

        for i in range(n - 1):
            key_joint = (int(y_t[i]), int(y_lag[i]), int(x_lag[i]))
            key_yy = (int(y_t[i]), int(y_lag[i]))
            key_ylag = int(y_lag[i])

            joint_counts[key_joint] = joint_counts.get(key_joint, 0) + 1
            y_y_counts[key_yy] = y_y_counts.get(key_yy, 0) + 1
            y_lag_counts[key_ylag] = y_lag_counts.get(key_ylag, 0) + 1

        total = n - 1
        te = 0.0
        for (yt, yl, xl), count_joint in joint_counts.items():
            p_joint = count_joint / total
            p_yy = y_y_counts.get((yt, yl), 0) / total
            p_ylag_xlag = count_joint / total  # p(y_t, y_{t-1}, x_{t-1})
            p_ylag = y_lag_counts.get(yl, 0) / total
            p_xlag_given_ylag = p_ylag_xlag / p_ylag if p_ylag > 0 else 0
            p_y_given_yy = p_joint / p_yy if p_yy > 0 else 0

            # Conditional probabilities
            p_y_given_ylag = sum(c for (y, yl2), c in y_y_counts.items() if yl2 == yl) / total
            p_y_given_ylag = p_y_given_ylag / p_ylag if p_ylag > 0 else 0

            if p_joint > 0 and p_y_given_yy > 0 and p_y_given_ylag > 0:
                te += p_joint * np.log(p_y_given_yy / p_y_given_ylag)

        return max(0, te)


# ============================================================
# A-20: EVOLUTIONARY — 演化与适应动力学
# ============================================================
class EvolutionaryAdapter:
    """A-20: 演化动力学与适应模型

    方法：
      1. 复制动力学（Replicator Dynamics, Taylor & Jonker 1978）
      2. 遗传算法演化优化
      3. 技术/政策扩散S曲线

    理论来源：Arthur (1994) "Increasing Returns and Path Dependence"
             Axelrod (1997) "The Complexity of Cooperation"
    """
    adapter_id = "A-20-EVOLUTIONARY"
    version = "4.5.0"
    disciplines = ["Evolutionary Biology", "Evolutionary Game Theory", "Innovation Economics"]
    theories = ["Replicator Dynamics", "Path Dependence (Arthur 1994)", "Bass Diffusion Model"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "replicator")  # replicator / diffusion / path_dependence
        if analysis_type == "replicator":
            return self._replicator_dynamics(data, params)
        elif analysis_type == "diffusion":
            return self._bass_diffusion(data, params)
        elif analysis_type == "path_dependence":
            return self._path_dependence(data, params)
        else:
            return {"error": f"Unknown: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    def _replicator_dynamics(self, data, params):
        """复制动力学：dx_i/dt = x_i * (f_i(x) - phi(x))"""
        payoff_matrix = np.asarray(data.get("payoff_matrix", [[3, 0], [5, 1]]), dtype=float)
        initial_freqs = np.asarray(data.get("initial_frequencies", [0.5, 0.5]), dtype=float)
        dt = float(params.get("dt", 0.01))
        n_steps = int(params.get("n_steps", 1000))

        freqs = initial_freqs.copy()
        history = [freqs.copy()]
        n = len(freqs)

        for _ in range(n_steps):
            fitness = payoff_matrix @ freqs
            avg_fitness = np.dot(freqs, fitness)
            df = freqs * (fitness - avg_fitness) * dt
            freqs = freqs + df
            freqs = np.clip(freqs, 0, 1)
            freqs = freqs / np.sum(freqs)
            history.append(freqs.copy())

        history = np.array(history)

        # Detect ESS
        final_freqs = history[-1]
        final_fitness = payoff_matrix @ final_freqs
        is_ess = np.allclose(final_fitness, np.max(final_fitness), atol=0.01)

        # Detect cyclic dynamics
        if n_steps > 200:
            late_phase = history[-200:, 0]
            cyclic = np.std(late_phase) > 0.01 and not is_ess
        else:
            cyclic = False

        return {
            "analysis": "replicator",
            "causal_grade": "C1",
            "causal_note": "Replicator dynamics describes selection process, not causal mechanism of fitness differences",
            "payoff_matrix": payoff_matrix.tolist(),
            "initial_frequencies": initial_freqs.tolist(),
            "final_frequencies": [round(float(f), 4) for f in final_freqs],
            "is_ess": bool(is_ess),
            "has_cyclic_dynamics": bool(cyclic),
            "convergence_time": int(np.where(np.abs(history[:, 0] - final_freqs[0]) < 0.01)[0][0]) if len(np.where(np.abs(history[:, 0] - final_freqs[0]) < 0.01)[0]) > 0 else n_steps,
            "interpretation": (
                f"System converged to ESS: strategy frequencies = {[round(float(f), 3) for f in final_freqs]}"
                if is_ess else
                f"Cyclic dynamics detected — Rock-Paper-Scissors-like oscillation"
                if cyclic else
                f"System evolving toward mixed equilibrium"
            ),
            "theory_ref": "Taylor & Jonker 1978, Maynard Smith 1982",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _bass_diffusion(self, data, params):
        """Bass创新扩散模型：f(t) = (p+qF)(1-F)"""
        # If data provided, fit p and q; else simulate
        adoption_data = data.get("cumulative_adoption", None)

        if adoption_data is not None:
            cumul = np.asarray(adoption_data, dtype=float)
            # Fit Bass model
            n = len(cumul)
            m = cumul[-1] * 1.05  # Market potential
            f = cumul / m
            f_shifted = np.roll(f, -1)[:-1]
            df = np.diff(f)
            f_current = f[:-1]

            # df/dt = p*(1-f) + q*f*(1-f)
            # Linearize: df/(1-f) = p + q*f
            y = df / (1 - f_current + 1e-10)
            X = np.column_stack([np.ones(len(f_current)), f_current])
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            p_fit = max(0, beta[0])
            q_fit = max(0, beta[1])
        else:
            p_fit = float(params.get("p", 0.03))  # Innovation coefficient
            q_fit = float(params.get("q", 0.38))  # Imitation coefficient
            m = float(params.get("market_size", 1000000))

        # Simulate
        dt = 0.1
        n_steps = int(params.get("n_steps", 100))
        f = 0.01
        trajectory = [f]
        for _ in range(n_steps):
            df = (p_fit + q_fit * f) * (1 - f) * dt
            f = min(1, f + df)
            trajectory.append(f)

        # Peak time: t* = 1/(p+q) * ln(q/p)
        if q_fit > p_fit > 0:
            peak_time = np.log(q_fit / p_fit) / (p_fit + q_fit)
        else:
            peak_time = None

        return {
            "analysis": "bass_diffusion",
            "causal_grade": "C1",
            "causal_note": "Bass model describes adoption patterns but external shocks and network effects can override",
            "p_innovation": round(float(p_fit), 6),
            "q_imitation": round(float(q_fit), 6),
            "peak_time": round(float(peak_time), 2) if peak_time is not None else None,
            "final_penetration": round(float(trajectory[-1]) * 100, 2),
            "interpretation": (
                f"Innovation-driven (p>q)" if p_fit > q_fit else
                f"Imitation-driven with peak at t={peak_time:.1f}" if peak_time else
                f"Slow diffusion"
            ),
            "theory_ref": "Bass 1969, Rogers 2003",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _path_dependence(self, data, params):
        """路径依赖：Polya urn模型"""
        n_steps = int(params.get("n_steps", 1000))
        initial_red = int(data.get("initial_red", 1))
        initial_blue = int(data.get("initial_blue", 1))
        alpha = float(params.get("reinforcement", 1.0))  # Reinforcement strength

        red = initial_red
        blue = initial_blue
        history = [red / (red + blue)]

        np.random.seed(42)
        for _ in range(n_steps):
            p_red = red / (red + blue)
            if np.random.random() < p_red:
                red += alpha
            else:
                blue += alpha
            history.append(red / (red + blue))

        final_red_ratio = history[-1]
        # Lock-in detected if ratio > 0.9 or < 0.1
        locked_in = final_red_ratio > 0.9 or final_red_ratio < 0.1

        return {
            "analysis": "path_dependence",
            "causal_grade": "C1",
            "causal_note": "Path dependence shows how early random events become frozen via positive feedback — historical contingency, not deterministic",
            "initial_ratio": round(initial_red / (initial_red + initial_blue), 4),
            "final_red_ratio": round(float(final_red_ratio), 4),
            "locked_in": bool(locked_in),
            "winner": "RED" if final_red_ratio > 0.5 else "BLUE",
            "interpretation": (
                f"{'Lock-in' if locked_in else 'Convergence'} achieved: {('RED' if final_red_ratio > 0.5 else 'BLUE')} dominates at {max(final_red_ratio, 1-final_red_ratio)*100:.1f}%"
            ),
            "theory_ref": "Arthur 1994, Page 2006",
            "validated": True,
            "adapter_id": self.adapter_id,
        }


# ============================================================
# A-21: COARSE_GRAINING — 多尺度粗粒化桥接
# ============================================================
class CoarseGrainingAdapter:
    """A-21: 多尺度粗粒化桥接（微观->中观->宏观）

    核心方法：
      1. 微观Agent状态 -> 粗粒化 -> 中观序参量
      2. 序参量动力学方程推断
      3. 尺度间信息损失量化

    理论来源：统计力学粗粒化、重整化群思想
    """
    adapter_id = "A-21-COARSE-GRAINING"
    version = "4.5.0"
    disciplines = ["Statistical Mechanics", "Multi-scale Modeling", "Physics"]
    theories = ["Coarse-Graining Operator", "Renormalization Group (Wilson)", "Order Parameters (Landau)"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis_type = params.get("analysis", "spatial")  # spatial / network / aggregate
        if analysis_type == "spatial":
            return self._spatial_coarse_graining(data, params)
        elif analysis_type == "network":
            return self._network_coarse_graining(data, params)
        elif analysis_type == "aggregate":
            return self._aggregate_bridge(data, params)
        else:
            return {"error": f"Unknown: {analysis_type}", "validated": False, "adapter_id": self.adapter_id}

    def _spatial_coarse_graining(self, data, params):
        """空间粗粒化：高分辨率场 -> 低分辨率场 + 信息保留评估"""
        micro_field = np.asarray(data.get("micro_field", []), dtype=float)
        if micro_field.ndim == 1:
            micro_field = micro_field.reshape(1, -1)

        block_size = int(params.get("block_size", 2))
        rows, cols = micro_field.shape

        # Block averaging coarse-graining
        macro_rows = rows // block_size
        macro_cols = cols // block_size
        macro_field = np.zeros((macro_rows, macro_cols))

        for i in range(macro_rows):
            for j in range(macro_cols):
                block = micro_field[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]
                macro_field[i, j] = np.mean(block)

        # Information loss: mutual information between micro and macro
        # Approximate via variance ratio
        micro_var = np.var(micro_field)
        macro_var = np.var(macro_field)
        info_retention = macro_var / micro_var if micro_var > 0 else 0

        # Order parameters
        mean_op = np.mean(macro_field)
        variance_op = np.var(macro_field)
        correlation_length = self._estimate_correlation_length(micro_field)

        return {
            "analysis": "spatial_coarse_graining",
            "causal_grade": "C1",
            "causal_note": "Coarse-graining is a mathematical operation, not causal. Information loss quantifies what is irreducibly lost at macro scale",
            "micro_shape": list(micro_field.shape),
            "macro_shape": list(macro_field.shape),
            "block_size": block_size,
            "compression_ratio": round(float(block_size ** 2), 2),
            "information_retention": round(float(info_retention), 4),
            "information_loss": round(float(1 - info_retention), 4),
            "order_parameters": {
                "mean": round(float(mean_op), 4),
                "variance": round(float(variance_op), 6),
                "correlation_length_pixels": round(float(correlation_length), 2),
            },
            "interpretation": (
                f"Compression {block_size}^2->1 retains {info_retention*100:.1f}% of variance. "
                f"{'Micro-scale fluctuations contain significant information' if info_retention < 0.5 else 'Macro description largely sufficient'}"
            ),
            "theory_ref": "Wilson RG, Kadanoff blocking",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _estimate_correlation_length(self, field):
        """估计相关长度"""
        if field.ndim == 2 and field.shape[0] > 1 and field.shape[1] > 1:
            center_y, center_x = field.shape[0] // 2, field.shape[1] // 2
            correlations = []
            max_r = min(center_x, center_y, 10)
            for r in range(1, max_r + 1):
                if center_y + r < field.shape[0] and center_x + r < field.shape[1]:
                    corr = np.corrcoef(field[center_y, :].flatten(),
                                       np.roll(field[center_y, :], r).flatten())[0, 1]
                    correlations.append(corr)
            if correlations and correlations[0] > 0:
                # Exponential decay fit
                try:
                    decay_rate = -np.log(max(correlations[-1], 0.01)) / len(correlations)
                    return 1 / decay_rate if decay_rate > 0 else float("inf")
                except Exception:
                    return 1.0
        return 1.0

    def _network_coarse_graining(self, data, params):
        """网络粗粒化：社区检测作为粗粒化算子"""
        adjacency = np.asarray(data.get("adjacency_matrix", []), dtype=float)
        if adjacency.ndim != 2 or adjacency.shape[0] < 3:
            return {"error": "Need adjacency matrix", "validated": False, "adapter_id": self.adapter_id}

        n = adjacency.shape[0]
        # Simplified community detection: spectral bisection
        degree = np.sum(adjacency, axis=1)
        D = np.diag(degree)
        L = D - adjacency

        # Fiedler vector
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(L)
            fiedler = eigenvectors[:, 1]
            communities = (fiedler > 0).astype(int)
        except Exception:
            communities = np.zeros(n, dtype=int)

        n_comm = len(np.unique(communities))

        # Inter-community vs intra-community edges
        intra_edges = 0
        inter_edges = 0
        for i in range(n):
            for j in range(i+1, n):
                if adjacency[i, j] > 0:
                    if communities[i] == communities[j]:
                        intra_edges += 1
                    else:
                        inter_edges += 1

        modularity = 0
        total_edges = intra_edges + inter_edges
        if total_edges > 0:
            for c in np.unique(communities):
                nodes_in_c = np.sum(communities == c)
                edges_in_c = sum(1 for i in range(n) for j in range(i+1, n)
                               if communities[i] == c and communities[j] == c and adjacency[i, j] > 0)
                modularity += edges_in_c / total_edges
                modularity -= (np.sum(degree[communities == c]) / (2 * total_edges)) ** 2

        return {
            "analysis": "network_coarse_graining",
            "causal_grade": "C1",
            "causal_note": "Community detection provides a coarse-graining of network structure. Modularity measures quality of this partition",
            "n_nodes_micro": n,
            "n_communities_macro": n_comm,
            "compression_ratio": round(float(n / n_comm), 2),
            "modularity": round(float(modularity), 4),
            "intra_edges": intra_edges,
            "inter_edges": inter_edges,
            "interpretation": f"Network compressed from {n} nodes to {n_comm} communities (modularity={modularity:.3f}). {'Strong community structure' if modularity > 0.3 else 'Weak community structure'}",
            "theory_ref": "Newman 2006, Fortunato 2010",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _aggregate_bridge(self, data, params):
        """微观->宏观聚合桥接：个体属性 -> 集体序参量"""
        individual_states = np.asarray(data.get("individual_states", []), dtype=float)
        if len(individual_states) < 2:
            return {"error": "Need >=2 individuals", "validated": False, "adapter_id": self.adapter_id}

        # Multiple order parameters
        order_params = {
            "mean": float(np.mean(individual_states)),
            "variance": float(np.var(individual_states)),
            "skewness": float(stats.skew(individual_states)),
            "kurtosis": float(stats.kurtosis(individual_states)),
            "polarization": self._polarization_index(individual_states),
            "consensus": self._consensus_index(individual_states),
        }

        # Phase classification
        if order_params["consensus"] > 0.8:
            phase = "ORDERED/CONSENSUS"
        elif order_params["polarization"] > 0.5:
            phase = "POLARIZED"
        elif order_params["variance"] > 0.2:
            phase = "DISORDERED"
        else:
            phase = "MIXED"

        return {
            "analysis": "aggregate_bridge",
            "causal_grade": "C1",
            "causal_note": "Order parameters describe collective state but do not explain how it emerged from individual interactions",
            "n_individuals": len(individual_states),
            "order_parameters": {k: round(float(v), 4) for k, v in order_params.items()},
            "phase": phase,
            "interpretation": f"Collective phase: {phase}. Mean={order_params['mean']:.3f}, Polarization={order_params['polarization']:.3f}",
            "theory_ref": "Landau phase transition theory, Galam sociophysics",
            "validated": True,
            "adapter_id": self.adapter_id,
        }

    def _polarization_index(self, states):
        """极化指数：双模态程度"""
        from scipy.stats import kurtosis
        return max(0, -kurtosis(states) / 3) if kurtosis(states) < 0 else 0

    def _consensus_index(self, states):
        """共识指数：集中度"""
        return 1 - np.std(states) / (np.max(states) - np.min(states) + 1e-10)
