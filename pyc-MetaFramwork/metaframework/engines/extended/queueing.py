"""M/M/c queueing engine."""

from __future__ import annotations

from math import factorial
from typing import Dict


class QueueingEngine:
    def execute(self, data: Dict[str, object], params: Dict[str, object]) -> Dict[str, object]:
        arrival_rate = float(data.get("task_arrival_rate", 5.0))
        service_rate = float(data.get("task_completion_rate", 1.0))
        max_team_size = int(params.get("max_team_size", 12))
        wait_cost_per_hour = float(params.get("wait_cost_per_hour", 100.0))
        person_cost_per_day = float(params.get("person_cost_per_day", 500.0))

        if arrival_rate >= service_rate * max_team_size:
            return {
                "success": False,
                "validated": False,
                "method": "QueueingMMc",
                "errors": ["System unstable: arrival rate exceeds max service capacity"],
            }

        results = []
        for team_size in range(1, max_team_size + 1):
            rho = arrival_rate / (team_size * service_rate)
            if rho >= 1:
                continue
            sum_terms = sum((arrival_rate / service_rate) ** k / factorial(k) for k in range(team_size))
            last_term = ((arrival_rate / service_rate) ** team_size / factorial(team_size)) * (1 / (1 - rho))
            p0 = 1 / (sum_terms + last_term)
            p_wait = last_term * p0
            wait_queue = p_wait / (team_size * service_rate - arrival_rate)
            total_time = wait_queue + 1 / service_rate
            wait_cost = arrival_rate * wait_queue * wait_cost_per_hour * 8
            labor_cost = team_size * person_cost_per_day
            total_cost = wait_cost + labor_cost
            results.append(
                {
                    "team_size": team_size,
                    "utilization": round(float(rho), 4),
                    "prob_wait": round(float(p_wait), 4),
                    "avg_wait_days": round(float(wait_queue), 4),
                    "avg_total_days": round(float(total_time), 4),
                    "total_cost": round(float(total_cost), 2),
                }
            )

        optimal = min(results, key=lambda item: item["total_cost"])
        service_level_met = [item for item in results if item["prob_wait"] < 0.1]
        return {
            "success": True,
            "validated": True,
            "method": "QueueingMMc",
            "evidence_level": "C1",
            "optimal_by_cost": optimal,
            "service_level_90pct_size": service_level_met[0]["team_size"] if service_level_met else None,
            "tradeoff_curve": results,
            "warnings": ["Queueing optimization is normative under arrival/service assumptions, not causal proof"],
        }
