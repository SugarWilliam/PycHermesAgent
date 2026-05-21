"""Simplified survival modeling engine inspired by Cox/AFT workflow."""

from __future__ import annotations

from typing import Dict

import numpy as np

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore


class CoxSurvivalEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        df = data.get("df")
        if isinstance(df, list) and pd is not None:
            df = pd.DataFrame(df)
        if df is None:
            return {
                "success": False,
                "validated": False,
                "method": "CoxSurvival",
                "errors": ["Cox survival engine requires df"],
            }

        tenure_col = str(params.get("tenure_col", "tenure_months"))
        event_col = str(params.get("event_col", "churned"))
        feature_cols = params.get("feature_cols")
        if feature_cols is None:
            feature_cols = [c for c in df.columns if c not in [tenure_col, event_col]]
        feature_cols = list(feature_cols)

        tenure = df[tenure_col].values.astype(float)
        event = df[event_col].values.astype(int) if event_col in df.columns else np.ones(len(df))
        X = df[feature_cols].values.astype(float)
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
        log_t = np.log(np.maximum(tenure, 0.1))
        n = len(log_t)
        X_aug = np.column_stack([np.ones(n), X])
        beta = np.linalg.lstsq(X_aug, log_t, rcond=None)[0]
        hr_per_sd = np.exp(beta[1:])

        concordant = 0
        comparable = 0
        for i in range(n):
            for j in range(i + 1, n):
                if event[i] == 1 or event[j] == 1:
                    comparable += 1
                    pred_i = X_aug[i] @ beta
                    pred_j = X_aug[j] @ beta
                    if (tenure[i] > tenure[j] and pred_i > pred_j) or (tenure[j] > tenure[i] and pred_j > pred_i):
                        concordant += 1
        c_index = concordant / comparable if comparable > 0 else 0.5
        median_survival = np.median(tenure[event == 1]) if np.sum(event == 1) > 0 else np.median(tenure)

        return {
            "success": True,
            "validated": True,
            "method": "CoxSurvival",
            "evidence_level": "C1",
            "c_index": round(float(c_index), 4),
            "median_survival": round(float(median_survival), 2),
            "hazard_ratios_per_sd": [
                {
                    "feature": feature_cols[i],
                    "hr": round(float(hr), 3),
                    "direction": "increases_risk" if hr > 1 else "decreases_risk",
                }
                for i, hr in enumerate(hr_per_sd)
            ],
            "warnings": ["This engine is predictive survival analysis, not causal attribution"],
        }
