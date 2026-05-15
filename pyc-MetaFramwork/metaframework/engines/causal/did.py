"""Minimal Difference-in-Differences engine for MetaFramework v0.1."""

from __future__ import annotations

from typing import Dict

import numpy as np


class DiDEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        treat_pre = np.asarray(data.get("treat_pre", []), dtype=float)
        treat_post = np.asarray(data.get("treat_post", []), dtype=float)
        control_pre = np.asarray(data.get("control_pre", []), dtype=float)
        control_post = np.asarray(data.get("control_post", []), dtype=float)

        if min(len(treat_pre), len(treat_post), len(control_pre), len(control_post)) == 0:
            return {
                "success": False,
                "validated": False,
                "method": "DiD",
                "errors": ["DiD requires treat/control pre/post arrays"],
            }

        delta_treat = float(np.mean(treat_post) - np.mean(treat_pre))
        delta_control = float(np.mean(control_post) - np.mean(control_pre))
        att = delta_treat - delta_control

        var = (
            np.var(treat_pre, ddof=1) / max(1, len(treat_pre))
            + np.var(treat_post, ddof=1) / max(1, len(treat_post))
            + np.var(control_pre, ddof=1) / max(1, len(control_pre))
            + np.var(control_post, ddof=1) / max(1, len(control_post))
        )
        se = float(np.sqrt(max(var, 0.0)))
        t_stat = att / se if se > 0 else 0.0
        significant = abs(t_stat) > 1.96

        return {
            "success": True,
            "validated": True,
            "method": "DiD-2x2",
            "evidence_level": "C3" if significant else "C2",
            "att": float(att),
            "delta_treat": delta_treat,
            "delta_control": delta_control,
            "standard_error": se,
            "t_stat": float(t_stat),
            "significant": bool(significant),
            "warnings": ["Parallel trends is an assumption and is not fully verified by this engine"],
        }
