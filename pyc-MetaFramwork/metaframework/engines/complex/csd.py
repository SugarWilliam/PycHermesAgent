"""Critical slowing down engine migrated from legacy tipping adapter."""

from __future__ import annotations

from typing import Dict

import numpy as np
from scipy.stats import kendalltau


class CSDEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        series = np.asarray(data.get("series", []), dtype=float)
        if len(series) < 50:
            return {
                "success": False,
                "validated": False,
                "method": "CSD",
                "errors": ["Need >=50 points for CSD detection"],
            }

        window_size = int(params.get("window_size", max(20, len(series) // 10)))
        step = int(params.get("step", max(5, window_size // 4)))
        ar1_values = []
        variance_values = []

        for start in range(0, len(series) - window_size, step):
            window = series[start:start + window_size]
            x = window[:-1]
            y = window[1:]
            ar1 = np.corrcoef(x, y)[0, 1] if np.std(x) > 0 else 0.0
            detrended = window - np.linspace(window[0], window[-1], len(window))
            ar1_values.append(ar1)
            variance_values.append(float(np.var(detrended)))

        tau_ar1, p_ar1 = kendalltau(range(len(ar1_values)), ar1_values)
        tau_var, p_var = kendalltau(range(len(variance_values)), variance_values)

        score = 0
        if p_ar1 < 0.05 and tau_ar1 > 0:
            score += 1
        if p_var < 0.05 and tau_var > 0:
            score += 1

        if score >= 2:
            risk = "HIGH"
        elif score == 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "success": True,
            "validated": True,
            "method": "CSD",
            "evidence_level": "C1",
            "risk_level": risk,
            "early_warning_score": score,
            "ar1_tau": float(tau_ar1),
            "ar1_p_value": float(p_ar1),
            "variance_tau": float(tau_var),
            "variance_p_value": float(p_var),
            "warnings": ["CSD is phenomenological and does not establish strong causality"],
        }
