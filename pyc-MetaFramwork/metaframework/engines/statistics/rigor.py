"""Statistical rigor engine based on MBB and BH-FDR."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import numpy as np


def block_bootstrap(
    data: np.ndarray,
    block_len: Optional[int] = None,
    n_boot: int = 1000,
    statistic_fn: Optional[Callable[[np.ndarray], float]] = None,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    if len(data) == 0:
        return {
            "estimates": np.array([]),
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "block_len": 0,
            "n_blocks": 0,
            "obs_stat": np.nan,
        }

    rng = np.random.default_rng(seed)
    T = len(data)
    if block_len is None:
        block_len = max(2, int(np.round(T ** (1 / 3))))
    block_len = min(block_len, T)
    n_blocks = max(1, int(np.ceil(T / block_len)))
    statistic_fn = statistic_fn or np.mean

    obs_stat = float(statistic_fn(data))
    estimates = np.zeros(n_boot)
    n_possible = T - block_len + 1
    blocks = np.array([data[i:i + block_len] for i in range(n_possible)])

    for i in range(n_boot):
        idx = rng.integers(0, n_possible, size=n_blocks)
        boot_series = np.concatenate(blocks[idx])[:T]
        estimates[i] = float(statistic_fn(boot_series))

    return {
        "estimates": estimates,
        "ci_lower": float(np.percentile(estimates, 100 * alpha / 2)),
        "ci_upper": float(np.percentile(estimates, 100 * (1 - alpha / 2))),
        "block_len": block_len,
        "n_blocks": n_blocks,
        "obs_stat": obs_stat,
    }


def fdr_correction(p_values: List[float], alpha: float = 0.05) -> Dict[str, Any]:
    m = len(p_values)
    if m == 0:
        return {
            "significant": [],
            "significant_idx": [],
            "n_total": 0,
            "n_significant": 0,
            "fdr_threshold": 0.0,
            "k_max": 0,
        }

    p_arr = np.asarray(p_values, dtype=float)
    sorted_idx = np.argsort(p_arr)
    sorted_p = p_arr[sorted_idx]
    k_max = 0
    for k in range(m, 0, -1):
        if sorted_p[k - 1] <= alpha * k / m:
            k_max = k
            break

    significant = np.zeros(m, dtype=bool)
    if k_max > 0:
        significant[sorted_idx[:k_max]] = True

    return {
        "significant": significant.tolist(),
        "significant_idx": [int(i) for i in np.where(significant)[0]],
        "n_total": m,
        "n_significant": int(k_max),
        "fdr_threshold": float(alpha * k_max / m) if k_max > 0 else 0.0,
        "k_max": int(k_max),
    }


def cusum_block_bootstrap_pvalues(
    data: np.ndarray,
    change_indices: List[int],
    n_boot: int = 1000,
    block_len: Optional[int] = None,
    window_factor: int = 5,
    seed: int = 42,
) -> List[float]:
    rng = np.random.default_rng(seed)
    data = np.asarray(data, dtype=float)
    T = len(data)
    if T == 0:
        return [1.0 for _ in change_indices]
    if block_len is None:
        block_len = max(2, int(np.round(T ** (1 / 3))))
    block_len = min(block_len, T)
    half_win = max(block_len * window_factor // 2, block_len)
    p_values = []

    for t in change_indices:
        w_start = max(0, t - half_win)
        w_end = min(T, t + half_win + 1)
        local = data[w_start:w_end]
        rel_t = t - w_start
        L = len(local)
        if rel_t < block_len or L - rel_t < block_len:
            p_values.append(1.0)
            continue

        pre = local[:rel_t]
        post = local[rel_t:]
        obs_stat = abs(np.mean(post) - np.mean(pre))
        boot_stats = np.zeros(n_boot)
        n_pre = len(pre)
        n_post = len(post)
        n_possible = L - block_len + 1
        blocks_pool = np.array([local[i:i + block_len] for i in range(n_possible)])
        n_blocks_total = max(1, int(np.ceil(L / block_len)))

        for i in range(n_boot):
            idx = rng.integers(0, n_possible, size=n_blocks_total)
            boot_series = np.concatenate(blocks_pool[idx])[:L]
            boot_pre = boot_series[:n_pre]
            boot_post = boot_series[n_pre:n_pre + n_post]
            boot_stats[i] = abs(np.mean(boot_post) - np.mean(boot_pre))

        p_values.append(float((np.sum(boot_stats >= obs_stat) + 1) / (n_boot + 1)))

    return p_values


def cusum_with_rigor(
    data: np.ndarray,
    change_indices: List[int],
    n_boot: int = 1000,
    block_len: Optional[int] = None,
    fdr_alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    p_values = cusum_block_bootstrap_pvalues(
        data=data,
        change_indices=change_indices,
        n_boot=n_boot,
        block_len=block_len,
        seed=seed,
    )
    fdr = fdr_correction(p_values, alpha=fdr_alpha)
    return {
        "candidate_indices": change_indices,
        "p_values": p_values,
        "significant_indices": [change_indices[i] for i in fdr["significant_idx"]],
        "n_candidates": len(change_indices),
        "n_significant": fdr["n_significant"],
        "report": f"{len(change_indices)} candidates / {fdr['n_significant']} FDR-significant",
        "fdr": fdr,
    }


class RigorEngine:
    def execute(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        series = np.asarray(data.get("series", []), dtype=float)
        change_indices = [int(i) for i in data.get("change_indices", [])]
        result = cusum_with_rigor(
            data=series,
            change_indices=change_indices,
            n_boot=int(params.get("n_boot", 500)),
            block_len=params.get("block_len"),
            fdr_alpha=float(params.get("fdr_alpha", 0.05)),
            seed=int(params.get("seed", 42)),
        )
        return {
            "success": True,
            "validated": True,
            "method": "MBB+BH-FDR",
            "evidence_level": "C1",
            **result,
        }
