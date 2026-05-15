"""Structural causal engine migrated from legacy structural causal adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore

try:
    import statsmodels.api as sm
    import scipy.stats as scipy_stats
    STATSMODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    sm = None  # type: ignore
    scipy_stats = None  # type: ignore
    STATSMODELS_AVAILABLE = False

try:
    from linearmodels.iv import IV2SLS
    LINEARMODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    IV2SLS = None  # type: ignore
    LINEARMODELS_AVAILABLE = False


class SCMEngine:
    def execute(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        df = data.get("df")
        if df is None:
            df = data.get("data")
        if isinstance(df, list) and pd is not None:
            df = pd.DataFrame(df)
        cause = data.get("cause") or params.get("cause")
        effect = data.get("effect") or params.get("effect")
        known_confounders = params.get("known_confounders") or data.get("known_confounders") or []
        instrument = params.get("instrument") or data.get("instrument")
        method = params.get("method", "auto")

        if df is None or cause is None or effect is None:
            return {
                "success": False,
                "validated": False,
                "errors": ["SCM requires df/data, cause, and effect"],
                "method": "SCM",
            }

        if method == "auto":
            if instrument is not None and hasattr(df, "columns") and instrument in df.columns:
                method = "instrumental"
            elif known_confounders:
                method = "backdoor"
            else:
                method = "unidentified"

        if method == "instrumental":
            return self._estimate_iv(df, cause, effect, instrument)
        if method == "backdoor":
            return self._estimate_backdoor(df, cause, effect, list(known_confounders))

        return {
            "success": True,
            "validated": True,
            "method": "SCM-unidentified",
            "estimate": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "p_value": 1.0,
            "identification": "unidentified",
            "evidence_level": "C2",
            "warnings": ["No valid identification strategy available"],
        }

    def _estimate_backdoor(self, df: Any, cause: str, effect: str, confounders: List[str]) -> Dict[str, Any]:
        try:
            y = np.asarray(df[effect], dtype=float)
            X_cols = [cause] + confounders
            X_raw = np.asarray(df[X_cols], dtype=float)
            X = np.column_stack([np.ones(len(X_raw)), X_raw])

            if STATSMODELS_AVAILABLE:
                model = sm.OLS(y, X).fit()
                estimate = float(model.params[1])
                ci = model.conf_int()[1]
                p_value = float(model.pvalues[1])
                ci_lower = float(ci[0])
                ci_upper = float(ci[1])
                warnings = []
            else:
                beta = np.linalg.lstsq(X, y, rcond=None)[0]
                resid = y - X @ beta
                dof = max(1, len(y) - X.shape[1])
                mse = np.sum(resid ** 2) / dof
                cov = mse * np.linalg.pinv(X.T @ X)
                se = float(np.sqrt(max(cov[1, 1], 0.0)))
                estimate = float(beta[1])
                if scipy_stats is not None and se > 0:
                    t_stat = estimate / se
                    p_value = float(2 * (1 - scipy_stats.t.cdf(abs(t_stat), df=dof)))
                else:
                    p_value = 1.0
                ci_lower = estimate - 1.96 * se
                ci_upper = estimate + 1.96 * se
                warnings = ["statsmodels unavailable, used numpy OLS fallback"]

            evidence = "C3" if p_value < 0.05 else "C2"
            return {
                "success": True,
                "validated": True,
                "method": "SCM-backdoor-OLS",
                "identification": "backdoor",
                "estimate": estimate,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "p_value": p_value,
                "evidence_level": evidence,
                "warnings": warnings,
            }
        except Exception as exc:
            return {
                "success": False,
                "validated": False,
                "method": "SCM-backdoor-OLS",
                "errors": [f"Backdoor estimation failed: {exc}"],
            }

    def _estimate_iv(self, df: Any, cause: str, effect: str, instrument: Optional[str]) -> Dict[str, Any]:
        if instrument is None:
            return {
                "success": False,
                "validated": False,
                "method": "SCM-IV",
                "errors": ["Instrumental identification requires instrument"],
            }
        if not LINEARMODELS_AVAILABLE:
            return {
                "success": True,
                "validated": False,
                "method": "SCM-IV",
                "estimate": np.nan,
                "ci_lower": np.nan,
                "ci_upper": np.nan,
                "p_value": 1.0,
                "evidence_level": "C2",
                "warnings": ["linearmodels unavailable, IV path downgraded"],
            }
        try:
            y = df[effect]
            X_endog = df[[cause]]
            Z_inst = df[[instrument]]
            const = pd.DataFrame({"const": np.ones(len(df))}, index=df.index)
            result = IV2SLS(dependent=y, exog=const, endog=X_endog, instruments=Z_inst).fit()
            estimate = float(result.params[cause])
            std_err = float(result.std_errors[cause])
            p_value = 2 * (1 - scipy_stats.t.cdf(abs(estimate / std_err), df=max(1, len(df) - 2))) if std_err > 0 else 1.0
            evidence = "C3+" if p_value < 0.05 else "C2"
            return {
                "success": True,
                "validated": True,
                "method": "SCM-IV-2SLS",
                "identification": "instrumental",
                "estimate": estimate,
                "ci_lower": estimate - 1.96 * std_err,
                "ci_upper": estimate + 1.96 * std_err,
                "p_value": float(p_value),
                "evidence_level": evidence,
            }
        except Exception as exc:
            return {
                "success": False,
                "validated": False,
                "method": "SCM-IV-2SLS",
                "errors": [f"IV estimation failed: {exc}"],
            }
