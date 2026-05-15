"""EVM project tracking engine."""

from __future__ import annotations

from typing import Dict

import numpy as np


class EVMEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        pv = np.asarray(data.get("planned_value", []), dtype=float)
        ev = np.asarray(data.get("earned_value", []), dtype=float)
        ac = np.asarray(data.get("actual_cost", []), dtype=float)
        bac = float(params.get("budget_at_completion", pv[-1] if len(pv) > 0 else 0.0))
        if min(len(pv), len(ev), len(ac)) < 3:
            return {
                "success": False,
                "validated": False,
                "method": "EVM",
                "errors": ["Need at least 3 points for planned_value, earned_value, and actual_cost"],
            }

        cpi = ev[-1] / ac[-1] if ac[-1] != 0 else 1.0
        spi = ev[-1] / pv[-1] if pv[-1] != 0 else 1.0
        cv = ev[-1] - ac[-1]
        sv = ev[-1] - pv[-1]
        eac_bac = bac / cpi if cpi != 0 else bac
        eac_combo = ac[-1] + (bac - ev[-1]) / (cpi * spi) if (cpi * spi) != 0 else bac
        etc = eac_bac - ac[-1]
        vac = bac - eac_bac
        tcpi = (bac - ev[-1]) / (bac - ac[-1]) if (bac - ac[-1]) != 0 else 1.0

        cpi_series = ev / np.maximum(ac, 1e-9)
        recent_window = min(10, len(cpi_series))
        recent_cpi = cpi_series[-recent_window:]
        rng = np.random.default_rng(int(params.get("seed", 42)))
        boot_means = []
        for _ in range(int(params.get("n_boot", 500))):
            boot = rng.choice(recent_cpi, size=recent_window, replace=True)
            boot_means.append(float(np.mean(boot)))
        ci_lower = float(np.percentile(boot_means, 2.5))
        ci_upper = float(np.percentile(boot_means, 97.5))
        planned_duration = float(params.get("planned_duration", len(pv)))
        forecast_duration = planned_duration / spi if spi > 0 else planned_duration * 2

        risk = "LOW"
        if cpi < 0.9 or spi < 0.9:
            risk = "HIGH"
        elif cpi < 0.95 or spi < 0.95:
            risk = "MEDIUM"

        return {
            "success": True,
            "validated": True,
            "method": "EVM",
            "evidence_level": "C1",
            "indices": {
                "cpi": round(float(cpi), 4),
                "spi": round(float(spi), 4),
                "cv": round(float(cv), 2),
                "sv": round(float(sv), 2),
            },
            "forecasts": {
                "eac_bac": round(float(eac_bac), 2),
                "eac_combo": round(float(eac_combo), 2),
                "etc": round(float(etc), 2),
                "vac": round(float(vac), 2),
                "tcpi": round(float(tcpi), 4),
                "forecast_duration": round(float(forecast_duration), 2),
            },
            "risk": risk,
            "cpi_ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
            "warnings": ["EVM is predictive and assumes future project dynamics resemble recent history"],
        }
