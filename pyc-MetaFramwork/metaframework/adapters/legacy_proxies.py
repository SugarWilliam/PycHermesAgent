"""Legacy-style adapter proxies over the v0.1 facade.

These proxies preserve the legacy `__call__(data=..., params=...)` shape while
running through the capability-governed MetaFramework v0.1 runtime.
"""

from __future__ import annotations

from typing import Any, Dict

from framework_v01 import MetaFramework


class _BaseProxy:
    capability_id = ""
    adapter_id = ""
    version = "0.1"

    def __init__(self) -> None:
        self._mf = MetaFramework()

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        result = self._mf.execute(
            {
                "capability_id": self.capability_id,
                "data": data,
                "params": params,
            }
        )
        payload = dict(result.get("payload", {}))
        payload["validated"] = result.get("validated", False)
        payload["adapter_id"] = self.adapter_id or self.capability_id
        payload["success"] = result.get("success", False)
        payload["warnings"] = result.get("warnings", [])
        payload["errors"] = result.get("errors", [])
        payload["evidence_level"] = result.get("evidence_level")
        if not result.get("success") and result.get("errors"):
            payload["error"] = "; ".join(result["errors"])
        return payload

    def _execute_capability(self, capability_id: str, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        result = self._mf.execute(
            {
                "capability_id": capability_id,
                "data": data,
                "params": params,
            }
        )
        payload = dict(result.get("payload", {}))
        payload["validated"] = result.get("validated", False)
        payload["adapter_id"] = self.adapter_id or capability_id
        payload["success"] = result.get("success", False)
        payload["warnings"] = result.get("warnings", [])
        payload["errors"] = result.get("errors", [])
        payload["evidence_level"] = result.get("evidence_level")
        if not result.get("success") and result.get("errors"):
            payload["error"] = "; ".join(result["errors"])
        return payload


class SCMAdapterProxy(_BaseProxy):
    capability_id = "causal.effect.scm"
    adapter_id = "A-12-SCM"
    disciplines = ["因果推断", "计量经济学"]
    theories = ["SCM", "Backdoor", "IV"]


class SyntheticControlAdapterProxy(_BaseProxy):
    capability_id = "causal.effect.synthetic_control"
    adapter_id = "A-12-SYNTH"
    disciplines = ["因果推断", "面板数据"]
    theories = ["Synthetic Control"]


class DiDAdapterProxy(_BaseProxy):
    capability_id = "causal.effect.did"
    adapter_id = "A-13-ORG-DID-LIMIT"
    disciplines = ["因果推断"]
    theories = ["Difference-in-Differences"]


class CSDAdapterProxy(_BaseProxy):
    capability_id = "complex.early_warning.csd"
    adapter_id = "A-16"
    disciplines = ["Complex Systems"]
    theories = ["Critical Slowing Down"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis = params.get("analysis", "csd")
        if analysis != "csd":
            return {
                "validated": False,
                "success": False,
                "adapter_id": self.adapter_id,
                "error": f"A-16 proxy only bridges analysis='csd' in v0.1, got: {analysis}",
                "warnings": ["Unsupported legacy branch kept outside current v0.1 bridge"],
                "errors": [f"Unsupported analysis: {analysis}"],
                "evidence_level": "C1",
            }
        return self._execute_capability(self.capability_id, data, params)


class PageRankAdapterProxy(_BaseProxy):
    capability_id = "network.centrality.pagerank"
    adapter_id = "A-22"
    disciplines = ["Network Science"]
    theories = ["PageRank"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis = params.get("analysis", "pagerank")
        if analysis == "pagerank":
            return self._execute_capability("network.centrality.pagerank", data, params)
        if analysis == "sir_network":
            return self._execute_capability("network.diffusion.sir", data, params)
        return {
            "validated": False,
            "success": False,
            "adapter_id": self.adapter_id,
            "error": f"A-22 proxy bridges only pagerank and sir_network in v0.1, got: {analysis}",
            "warnings": ["Percolation and cascade remain on the legacy implementation path"],
            "errors": [f"Unsupported analysis: {analysis}"],
            "evidence_level": "C1",
        }


class KalmanGoalAdapterProxy(_BaseProxy):
    capability_id = "extended.state.kalman_goal"
    adapter_id = "A-14-PERS-GOAL-LIMIT"
    disciplines = ["State Space Models"]
    theories = ["Kalman Filter"]


class HabitHMMAdapterProxy(_BaseProxy):
    capability_id = "extended.state.habit_hmm"
    adapter_id = "A-14-PERS-HABIT-LIMIT"
    disciplines = ["Sequential Models"]
    theories = ["Hidden Markov Model"]


class CoxAdapterProxy(_BaseProxy):
    capability_id = "extended.survival.cox"
    adapter_id = "A-13-ORG-CHURN-LIMIT"
    disciplines = ["Survival Analysis"]
    theories = ["Cox", "AFT"]


class DEAAdapterProxy(_BaseProxy):
    capability_id = "extended.efficiency.dea"
    adapter_id = "A-15-TEAM-PROD-LIMIT"
    disciplines = ["Operations Research"]
    theories = ["DEA CCR"]


class MMcQueueingAdapterProxy(_BaseProxy):
    capability_id = "extended.queueing.mmc"
    adapter_id = "A-15-TEAM-SIZE-LIMIT"
    disciplines = ["Queueing Theory"]
    theories = ["M/M/c", "Erlang C"]


class OrganizationAdapterProxy(_BaseProxy):
    capability_id = "causal.effect.did"
    adapter_id = "A-13"
    disciplines = ["Organization Science", "Project Management", "HR Analytics"]
    theories = ["Difference-in-Differences", "Survival Analysis"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis = params.get("analysis", "evm")
        if analysis == "evm":
            return self._execute_capability("extended.project.evm", data, params)
        if analysis == "org_change":
            if "df" in data and data.get("df") is not None:
                df = data["df"]
                treat_pre = df[(df["treated"] == 1) & (df["post"] == 0)]["y"].tolist()
                treat_post = df[(df["treated"] == 1) & (df["post"] == 1)]["y"].tolist()
                control_pre = df[(df["treated"] == 0) & (df["post"] == 0)]["y"].tolist()
                control_post = df[(df["treated"] == 0) & (df["post"] == 1)]["y"].tolist()
                translated = {
                    "treat_pre": treat_pre,
                    "treat_post": treat_post,
                    "control_pre": control_pre,
                    "control_post": control_post,
                }
            else:
                y = data.get("y", [])
                treated = data.get("treated", [])
                post = data.get("post", [])
                translated = {
                    "treat_pre": [val for val, tr, po in zip(y, treated, post) if tr == 1 and po == 0],
                    "treat_post": [val for val, tr, po in zip(y, treated, post) if tr == 1 and po == 1],
                    "control_pre": [val for val, tr, po in zip(y, treated, post) if tr == 0 and po == 0],
                    "control_post": [val for val, tr, po in zip(y, treated, post) if tr == 0 and po == 1],
                }
            return self._execute_capability("causal.effect.did", translated, params)
        if analysis == "churn":
            return self._execute_capability("extended.survival.cox", data, params)
        return {
            "validated": False,
            "success": False,
            "adapter_id": self.adapter_id,
            "error": f"A-13 proxy bridges only analysis='org_change' and 'churn' in v0.1, got: {analysis}",
            "warnings": ["EVM remains on the legacy implementation path"],
            "errors": [f"Unsupported analysis: {analysis}"],
            "evidence_level": "C1",
        }


class PersonalGrowthAdapterProxy(_BaseProxy):
    capability_id = "extended.state.kalman_goal"
    adapter_id = "A-14"
    disciplines = ["Behavioral Science", "Learning Analytics"]
    theories = ["HMM", "Kalman Filter"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis = params.get("analysis", "learning")
        if analysis == "learning":
            return self._execute_capability("extended.learning.curve", data, params)
        if analysis == "habit":
            habit_data = {"compliance": data.get("compliance", [])}
            return self._execute_capability("extended.state.habit_hmm", habit_data, params)
        if analysis == "goal":
            progress_series = data.get("progress_series")
            if progress_series is None:
                historical_goals = data.get("historical_goals", [])
                current_progress = float(data.get("current_progress", 0.5))
                progress_series = list(historical_goals) + [current_progress]
            return self._execute_capability("extended.state.kalman_goal", {"progress_series": progress_series}, params)
        return {
            "validated": False,
            "success": False,
            "adapter_id": self.adapter_id,
            "error": f"A-14 proxy bridges only analysis='learning', 'habit', and 'goal' in v0.1, got: {analysis}",
            "warnings": ["Unsupported legacy branch kept outside current v0.1 bridge"],
            "errors": [f"Unsupported analysis: {analysis}"],
            "evidence_level": "C1",
        }


class TeamManagementAdapterProxy(_BaseProxy):
    capability_id = "extended.efficiency.dea"
    adapter_id = "A-15"
    disciplines = ["Team Science", "Operations Research"]
    theories = ["DEA", "Queueing"]

    def __call__(self, *, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        analysis = params.get("analysis", "productivity")
        if analysis == "productivity":
            teams = data.get("teams")
            if teams is None:
                members = data.get("members", [])
                if members:
                    skill_mean = sum(m.get("skill", 0.5) for m in members) / len(members)
                    motivation_mean = sum(m.get("motivation", 0.5) for m in members) / len(members)
                else:
                    skill_mean = 0.5
                    motivation_mean = 0.5
                current_team = {
                    "inputs": [float(len(members) or 3), float(len(members) or 3)],
                    "outputs": [skill_mean * 100, motivation_mean * 100],
                }
                teams = [
                    current_team,
                    {"inputs": [4, 4], "outputs": [65, 70]},
                    {"inputs": [5, 5], "outputs": [80, 78]},
                ]
            return self._execute_capability("extended.efficiency.dea", {"teams": teams}, params)
        if analysis == "conflict":
            return self._execute_capability("extended.team.conflict_signal", data, params)
        if analysis == "optimal_size":
            queue_data = {
                "task_arrival_rate": data.get("task_arrival_rate", 5.0),
                "task_completion_rate": data.get("task_completion_rate", 1.0),
            }
            return self._execute_capability("extended.queueing.mmc", queue_data, params)
        return {
            "validated": False,
            "success": False,
            "adapter_id": self.adapter_id,
            "error": f"A-15 proxy bridges only analysis='productivity', 'conflict', and 'optimal_size' in v0.1, got: {analysis}",
            "warnings": ["Unsupported legacy branch kept outside current v0.1 bridge"],
            "errors": [f"Unsupported analysis: {analysis}"],
            "evidence_level": "C1",
        }
