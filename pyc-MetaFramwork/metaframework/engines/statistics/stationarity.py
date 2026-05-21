"""Minimal stationarity helpers migrated from legacy stats module."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np


def adf_like(series: np.ndarray) -> Dict[str, float]:
    x = np.asarray(series, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return {"t_stat": np.nan, "p_value": 1.0, "is_stationary": False, "n": n}
    dx = np.diff(x)
    if len(dx) < 5:
        return {"t_stat": np.nan, "p_value": 1.0, "is_stationary": False, "n": n}
    y = dx[1:]
    x_lag = x[1:-1]
    dx_lag = dx[:-1]
    X = np.column_stack([np.ones(len(y)), x_lag, dx_lag])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    mse = np.sum(resid ** 2) / max(1, (len(y) - 3))
    var_beta = mse * np.linalg.pinv(X.T @ X)
    se_beta1 = np.sqrt(var_beta[1, 1]) if var_beta.shape[0] > 1 else np.nan
    t_stat = beta[1] / se_beta1 if se_beta1 > 0 else np.nan
    p_value = 0.95 if t_stat > -1.95 else 0.05 if t_stat < -2.86 else 0.5
    return {"t_stat": float(t_stat), "p_value": float(p_value), "is_stationary": bool(t_stat < -2.86), "n": n}


def make_stationary(series: np.ndarray, max_diff: int = 2) -> Tuple[np.ndarray, int, Dict[str, float]]:
    x = np.asarray(series, dtype=float)
    result = adf_like(x)
    for diff_order in range(max_diff + 1):
        result = adf_like(x)
        if result["is_stationary"]:
            return x, diff_order, result
        x = np.diff(x)
    return x, max_diff, result
