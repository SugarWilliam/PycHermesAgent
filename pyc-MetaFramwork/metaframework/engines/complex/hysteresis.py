"""Hysteresis detection engine."""

from __future__ import annotations

from typing import Dict

import numpy as np


class HysteresisEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        x_forward = np.asarray(data.get("x_forward", []), dtype=float)
        y_forward = np.asarray(data.get("y_forward", []), dtype=float)
        x_reverse = np.asarray(data.get("x_reverse", []), dtype=float)
        y_reverse = np.asarray(data.get("y_reverse", []), dtype=float)
        if min(len(x_forward), len(y_forward), len(x_reverse), len(y_reverse)) < 3:
            return {
                "success": False,
                "validated": False,
                "method": "Hysteresis",
                "errors": ["Need forward and reverse sweep data with >=3 points each"],
            }

        y_rev_interp = np.interp(x_forward, x_reverse, y_reverse)
        deviation = y_forward - y_rev_interp
        mean_deviation = np.mean(np.abs(deviation))
        y_range = np.max(np.concatenate([y_forward, y_reverse])) - np.min(np.concatenate([y_forward, y_reverse]))
        hysteresis_index = mean_deviation / y_range if y_range > 0 else 0.0
        has_hysteresis = bool(hysteresis_index > 0.1)
        loop_x = np.concatenate([x_forward, x_reverse[::-1]])
        loop_y = np.concatenate([y_forward, y_reverse[::-1]])
        loop_area = 0.5 * np.abs(np.sum(loop_x[:-1] * loop_y[1:] - loop_x[1:] * loop_y[:-1]))

        return {
            "success": True,
            "validated": True,
            "method": "Hysteresis",
            "evidence_level": "C2",
            "has_hysteresis": has_hysteresis,
            "hysteresis_index": round(float(hysteresis_index), 4),
            "loop_area": round(float(loop_area), 4),
            "warnings": ["Hysteresis indicates path dependence but is not intervention-grade evidence"],
        }
