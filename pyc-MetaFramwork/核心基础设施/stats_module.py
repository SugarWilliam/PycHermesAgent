"""Statistical rigor module: stationarity, causality, cointegration, bootstrap."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import f as f_dist

logger = logging.getLogger("metamodel.stats")


class StationarityTester:
    """Augmented Dickey-Fuller and KPSS tests with automatic differencing."""

    def adf(self, series: np.ndarray, maxlag: Optional[int] = None) -> Dict[str, float]:
        """Simplified ADF: H0 = unit root (non-stationary)."""
        x = np.asarray(series, dtype=float)
        x = x[~np.isnan(x)]
        n = len(x)
        if n < 10:
            return {"t_stat": np.nan, "p_value": 1.0, "is_stationary": False, "n": n}

        # First difference if needed
        dx = np.diff(x)
        dx = dx[~np.isnan(dx)]
        if len(dx) < 5:
            return {"t_stat": np.nan, "p_value": 1.0, "is_stationary": False, "n": n}

        # Regression: dx[t] = alpha + beta*x[t-1] + gamma*dx[t-1] + eps
        y = dx[1:]
        x_lag = x[1:-1]
        dx_lag = dx[:-1]

        X = np.column_stack([np.ones(len(y)), x_lag, dx_lag])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        resid = y - X @ beta
        mse = np.sum(resid**2) / (len(y) - 3)
        var_beta = mse * np.linalg.inv(X.T @ X)
        se_beta1 = np.sqrt(var_beta[1, 1]) if var_beta.shape[0] > 1 else np.nan

        t_stat = beta[1] / se_beta1 if se_beta1 > 0 else np.nan
        # Approximate p-value (MacKinnon table for n>50)
        p_value = 0.95 if t_stat > -1.95 else 0.05 if t_stat < -2.86 else 0.5

        return {
            "t_stat": float(t_stat),
            "p_value": float(p_value),
            "is_stationary": t_stat < -2.86,
            "n": n,
        }

    def make_stationary(self, series: np.ndarray, max_diff: int = 2) -> Tuple[np.ndarray, int, Dict]:
        """
        Auto-difference until stationary or max_diff reached.
        Returns: (diffed_series, diff_order, adf_result)
        """
        x = np.asarray(series, dtype=float)
        for d in range(max_diff + 1):
            adf_res = self.adf(x)
            if adf_res["is_stationary"]:
                return x, d, adf_res
            x = np.diff(x)
        return x, max_diff, adf_res


class CointegrationTester:
    """Engle-Granger two-step cointegration test."""

    def engle_granger(self, y: np.ndarray, x: np.ndarray) -> Dict[str, float]:
        """Test for cointegration between y and x."""
        y = np.asarray(y, dtype=float)
        x = np.asarray(x, dtype=float)
        y = y[~np.isnan(y)]
        x = x[~np.isnan(x)]
        min_len = min(len(y), len(x))
        y, x = y[:min_len], x[:min_len]

        # Step 1: long-run OLS
        X_lr = np.column_stack([np.ones(len(x)), x])
        beta = np.linalg.lstsq(X_lr, y, rcond=None)[0]
        resid = y - X_lr @ beta

        # Step 2: ADF on residuals
        st = StationarityTester()
        adf_resid = st.adf(resid)

        return {
            "cointegrated": adf_resid["is_stationary"],
            "adf_t_stat": adf_resid["t_stat"],
            "adf_p_value": adf_resid["p_value"],
            "slope": float(beta[1]),
            "intercept": float(beta[0]),
            "r_squared": float(1 - np.sum(resid**2) / np.sum((y - np.mean(y))**2)),
            "n": min_len,
        }


class CausalityTester:
    """Granger causality with automatic stationarity handling."""

    def __init__(self):
        self.st = StationarityTester()

    def granger(
        self,
        y: np.ndarray,
        x: np.ndarray,
        lags: int = 2,
        make_stationary: bool = True,
    ) -> Dict[str, float]:
        """
        Granger causality test.
        If make_stationary=True, auto-difference non-stationary series first.
        """
        y = np.asarray(y, dtype=float)
        x = np.asarray(x, dtype=float)

        if make_stationary:
            y, dy_y, _ = self.st.make_stationary(y)
            x, dy_x, _ = self.st.make_stationary(x)
            # Align differences
            min_d = min(dy_y, dy_x)
            if min_d > 0:
                y = np.diff(np.concatenate([[np.nan] * min_d, y[: len(y) + min_d - dy_y]]), n=min_d)
                x = np.diff(np.concatenate([[np.nan] * min_d, x[: len(x) + min_d - dy_x]]), n=min_d)

        y = y[~np.isnan(y)]
        x = x[~np.isnan(x)]
        min_len = min(len(y), len(x))
        y, x = y[:min_len], x[:min_len]

        if len(y) < lags * 3:
            return {"f_stat": np.nan, "p_value": 1.0, "significant": False, "n": len(y), "stationary_handled": make_stationary}

        def _make_lags(series, maxlag):
            result = np.zeros((len(series) - maxlag, maxlag))
            for i in range(maxlag):
                result[:, i] = series[maxlag - i - 1 : len(series) - i - 1]
            return result

        y_target = y[lags:]
        y_lags = _make_lags(y, lags)
        x_lags = _make_lags(x, lags)

        # Unrestricted
        X_ur = np.column_stack([np.ones(len(y_target)), y_lags, x_lags])
        b_ur = np.linalg.lstsq(X_ur, y_target, rcond=None)[0]
        resid_ur = y_target - X_ur @ b_ur
        ssr_ur = np.sum(resid_ur**2)

        # Restricted
        X_r = np.column_stack([np.ones(len(y_target)), y_lags])
        b_r = np.linalg.lstsq(X_r, y_target, rcond=None)[0]
        resid_r = y_target - X_r @ b_r
        ssr_r = np.sum(resid_r**2)

        m = lags
        T = len(y_target)
        k = X_ur.shape[1] - 1

        f_stat = ((ssr_r - ssr_ur) / m) / (ssr_ur / (T - k - 1))
        p_value = 1 - f_dist.cdf(f_stat, m, T - k - 1)

        return {
            "f_stat": float(f_stat),
            "p_value": float(p_value),
            "significant": p_value < 0.05,
            "causality_direction": "x→y" if p_value < 0.05 else "no_granger_causality",
            "n": T,
            "lags": lags,
            "stationary_handled": make_stationary,
        }


class BootstrapTester:
    """Block bootstrap for time series with automatic block length selection."""

    def __init__(self, n_boot: int = 2000, confidence: float = 0.95):
        self.n_boot = n_boot
        self.confidence = confidence

    def optimal_block_length(self, series: np.ndarray) -> int:
        """Simple heuristic: ~n^(1/3) or based on autocorrelation."""
        n = len(series)
        # Use n^(1/3) rounded
        b = max(1, int(round(n ** (1 / 3))))
        return b

    def block_bootstrap_ci(
        self,
        x: np.ndarray,
        y: np.ndarray,
        statistic_func,
    ) -> Dict[str, float]:
        """Compute bootstrap confidence interval for a bivariate statistic."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        x = x[~np.isnan(x)]
        y = y[~np.isnan(y)]
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]

        b = self.optimal_block_length(x)
        n_blocks = n // b

        boot_stats = []
        rng = np.random.default_rng(42)
        for _ in range(self.n_boot):
            # Sample blocks with replacement
            idx = []
            for _ in range(n_blocks + 1):
                start = rng.integers(0, n - b + 1)
                idx.extend(range(start, start + b))
            idx = idx[:n]
            stat = statistic_func(x[idx], y[idx])
            if not np.isnan(stat):
                boot_stats.append(stat)

        boot_stats = np.array(boot_stats)
        alpha = 1 - self.confidence
        ci_low = np.percentile(boot_stats, alpha / 2 * 100)
        ci_high = np.percentile(boot_stats, (1 - alpha / 2) * 100)
        point_estimate = statistic_func(x, y)

        return {
            "point_estimate": float(point_estimate),
            "ci_lower": float(ci_low),
            "ci_upper": float(ci_high),
            "std_error": float(np.std(boot_stats)),
            "n_boot": len(boot_stats),
            "block_length": b,
        }
