"""Kalman-based progress tracking engine."""

from __future__ import annotations

from typing import Dict

import numpy as np


class KalmanGoalEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        progress_series = np.asarray(data.get("progress_series", []), dtype=float)
        if len(progress_series) < 3:
            return {
                "success": False,
                "validated": False,
                "method": "KalmanGoal",
                "errors": ["Need >=3 progress observations for Kalman tracking"],
            }

        n = len(progress_series)
        theta_est = np.zeros(n)
        p_est = np.zeros(n)
        theta_est[0] = progress_series[0]
        p_est[0] = 0.1

        q = float(params.get("process_noise", 0.01))
        r = float(params.get("measurement_noise", max(np.var(progress_series) * 0.5, 1e-6)))

        for t in range(1, n):
            theta_pred = theta_est[t - 1]
            p_pred = p_est[t - 1] + q
            kalman_gain = p_pred / (p_pred + r)
            theta_est[t] = theta_pred + kalman_gain * (progress_series[t] - theta_pred)
            p_est[t] = (1 - kalman_gain) * p_pred

        current_theta = float(theta_est[-1])
        current_p = float(p_est[-1])
        trend = float(np.mean(np.diff(theta_est[-5:]))) if n >= 5 else float(np.mean(np.diff(theta_est)))

        if (current_theta + trend) > progress_series[-1] and trend > 0:
            rng = np.random.default_rng(int(params.get("seed", 42)))
            days_needed = []
            for _ in range(int(params.get("n_sim", 300))):
                theta_sim = current_theta + rng.normal(0, np.sqrt(max(current_p, 1e-9)))
                proj = float(progress_series[-1])
                days = 0
                while proj < 1.0 and days < 365:
                    proj += max(0.0, theta_sim + trend * days + rng.normal(0, np.sqrt(r)))
                    days += 1
                days_needed.append(days)
            days_median = int(np.median(days_needed))
            days_ci = [int(np.percentile(days_needed, 10)), int(np.percentile(days_needed, 90))]
            prob_30d = float(np.mean(np.asarray(days_needed) <= 30) * 100)
        else:
            days_median = None
            days_ci = [None, None]
            prob_30d = 0.0

        return {
            "success": True,
            "validated": True,
            "method": "KalmanGoal",
            "evidence_level": "C1",
            "current_capability_estimate": round(current_theta, 4),
            "capability_uncertainty": round(float(np.sqrt(max(current_p, 0.0))), 4),
            "detected_trend": round(trend, 6),
            "predicted_days_to_complete": days_median,
            "days_ci_80": days_ci,
            "prob_complete_30d": round(prob_30d, 2),
            "warnings": ["Kalman tracking is descriptive and predictive, not causal"],
        }
