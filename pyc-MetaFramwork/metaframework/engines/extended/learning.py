"""Learning curve engine based on Wright's power law."""

from __future__ import annotations

from typing import Dict

import numpy as np


class LearningCurveEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        trials = np.asarray(data.get("trials", []), dtype=float)
        performance = np.asarray(data.get("performance", []), dtype=float)
        if min(len(trials), len(performance)) < 3:
            return {
                "success": False,
                "validated": False,
                "method": "LearningCurve",
                "errors": ["Need >=3 trials and performance points"],
            }

        log_n = np.log(trials)
        log_perf = np.log(np.maximum(performance, 1e-9))
        X = np.column_stack([np.ones(len(log_n)), log_n])
        beta = np.linalg.lstsq(X, log_perf, rcond=None)[0]
        log_t1, neg_b = beta
        b = -float(neg_b)
        t1 = float(np.exp(log_t1))

        y_pred = X @ beta
        ss_res = np.sum((log_perf - y_pred) ** 2)
        ss_tot = np.sum((log_perf - np.mean(log_perf)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        rng = np.random.default_rng(int(params.get("seed", 42)))
        boot_bs = []
        for _ in range(int(params.get("n_boot", 500))):
            idx = rng.choice(len(log_n), size=len(log_n), replace=True)
            beta_boot = np.linalg.lstsq(X[idx], log_perf[idx], rcond=None)[0]
            boot_bs.append(float(-beta_boot[1]))
        b_ci = [float(np.percentile(boot_bs, 2.5)), float(np.percentile(boot_bs, 97.5))]

        future_trials = np.arange(int(np.max(trials)) + 1, int(np.max(trials)) + int(params.get("forecast_trials", 10)) + 1)
        future_perf = t1 * future_trials ** (-b)
        mastery_threshold = params.get("mastery_threshold")
        mastery_trial = None
        if mastery_threshold is not None and b > 0 and t1 > float(mastery_threshold):
            mastery_trial = int(np.ceil((t1 / float(mastery_threshold)) ** (1 / b)))
        marginal_improvement = b * t1 * (int(np.max(trials)) + 1) ** (-b - 1)

        return {
            "success": True,
            "validated": True,
            "method": "LearningCurve",
            "evidence_level": "C1",
            "learning_rate_b": round(b, 4),
            "b_ci_95": [round(b_ci[0], 4), round(b_ci[1], 4)],
            "initial_performance_t1": round(t1, 4),
            "r_squared": round(float(r_squared), 4),
            "future_predictions": [
                {"trial": int(t), "predicted_performance": round(float(p), 4)}
                for t, p in zip(future_trials, future_perf)
            ],
            "mastery": {
                "threshold": mastery_threshold,
                "predicted_trial_to_mastery": mastery_trial,
            } if mastery_threshold is not None else None,
            "plateau_warning": bool(marginal_improvement < 0.01 * t1),
            "marginal_improvement": round(float(marginal_improvement), 6),
            "warnings": ["Learning curve fit is predictive, not causal"],
        }
