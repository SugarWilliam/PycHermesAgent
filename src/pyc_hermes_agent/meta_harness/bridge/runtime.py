"""Controlled bridge into legacy `pyc-MetaFramwork` modules."""

from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterator, Optional

import numpy as np


# Keep the MVP bridge limited to legacy surfaces with stable local contracts or
# explicit numpy fallbacks. Heavier legacy families stay degraded until the
# harness models their dependency availability more explicitly.
_RUNTIME_DISABLED_MODULE_ERRORS = {
    "org_personal_adapters": (
        "Legacy org_personal_adapters execution is disabled in the current MVP bridge "
        "because it depends on optional pandas/scipy stacks."
    ),
    "complex_systems_adapters": (
        "Legacy complex_systems_adapters execution is disabled in the current MVP bridge "
        "because it depends on optional pandas/scipy stacks."
    ),
    "stats_module": (
        "Legacy stats_module execution is disabled in the current MVP bridge; "
        "use statistical_rigor or method-specific routes instead."
    ),
}


@dataclass(slots=True)
class LegacyModuleStatus:
    module_name: str
    module: Optional[ModuleType]
    path: Optional[Path]
    available: bool
    error: Optional[str] = None


def _find_legacy_infra_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "pyc-MetaFramwork" / "核心基础设施"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate pyc-MetaFramwork/核心基础设施")


@contextmanager
def _legacy_sys_path(legacy_root: Path) -> Iterator[None]:
    path_str = str(legacy_root)
    sys.path.insert(0, path_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(path_str)
        except ValueError:
            pass


class LegacyMetaBridge:
    def __init__(self, legacy_root: Optional[Path] = None) -> None:
        self.legacy_root = legacy_root or _find_legacy_infra_root()

    def status(self, module_name: str) -> LegacyModuleStatus:
        module_path = self.legacy_root / f"{module_name}.py"
        if not module_path.exists():
            return LegacyModuleStatus(
                module_name=module_name,
                module=None,
                path=None,
                available=False,
                error=f"Legacy module not found: {module_name}",
            )

        disabled_error = _RUNTIME_DISABLED_MODULE_ERRORS.get(module_name)
        if disabled_error is not None:
            return LegacyModuleStatus(
                module_name=module_name,
                module=None,
                path=module_path,
                available=False,
                error=disabled_error,
            )

        cached = sys.modules.get(module_name)
        if cached is not None and getattr(cached, "__file__", None) == str(module_path):
            return LegacyModuleStatus(
                module_name=module_name,
                module=cached,
                path=module_path,
                available=True,
            )

        try:
            with _legacy_sys_path(self.legacy_root):
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not create import spec for {module_name}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            return LegacyModuleStatus(
                module_name=module_name,
                module=module,
                path=module_path,
                available=True,
            )
        except Exception as exc:
            sys.modules.pop(module_name, None)
            return LegacyModuleStatus(
                module_name=module_name,
                module=None,
                path=module_path,
                available=False,
                error=str(exc),
            )

    def execute(self, capability_id: str, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        if capability_id == "A-12-FORECAST":
            return self.run_forecast(data, params)
        if capability_id == "A-12-SCM":
            return self.run_structural_causal(data, params)
        if capability_id == "A-13":
            return self.run_organization(data, params)
        if capability_id == "A-14":
            return self.run_personal_growth(data, params)
        if capability_id == "A-15":
            return self.run_team_management(data, params)
        if capability_id == "A-18":
            return self.run_causal_emergence(data, params)
        if capability_id == "A-22":
            return self.run_network_science(data, params)
        if capability_id == "A-23":
            return self.run_abm(data, params)
        return {
            "validated": False,
            "status": "not_implemented",
            "error": f"No bridge execution path for capability {capability_id}.",
            "adapter_id": capability_id,
        }

    def run_forecast(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        status = self.status("forecast_adapters")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "forecast_adapters unavailable",
                "adapter_id": "A-12-FORECAST",
            }

        adapter_cls = getattr(status.module, "ForecastAdapter", None)
        if adapter_cls is None:
            return {
                "validated": False,
                "status": "invalid_legacy_module",
                "error": "ForecastAdapter not found in legacy forecast_adapters module",
                "adapter_id": "A-12-FORECAST",
            }

        try:
            return adapter_cls()(data=data, params=params)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
                "adapter_id": "A-12-FORECAST",
            }

    def run_organization(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_org_family_adapter("OrganizationAdapter", "A-13", data, params)

    def run_personal_growth(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_org_family_adapter("PersonalGrowthAdapter", "A-14", data, params)

    def run_team_management(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_org_family_adapter("TeamManagementAdapter", "A-15", data, params)

    def _run_org_family_adapter(
        self,
        class_name: str,
        adapter_id: str,
        data: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        status = self.status("org_personal_adapters")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "org_personal_adapters unavailable",
                "adapter_id": adapter_id,
            }

        adapter_cls = getattr(status.module, class_name, None)
        if adapter_cls is None:
            return {
                "validated": False,
                "status": "invalid_legacy_module",
                "error": f"{class_name} not found in legacy org_personal_adapters module",
                "adapter_id": adapter_id,
            }

        try:
            return adapter_cls()(data=data, params=params)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
                "adapter_id": adapter_id,
            }

    def run_structural_causal(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        status = self.status("structural_causal")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "structural_causal unavailable",
                "adapter_id": "A-12-SCM",
            }

        if not getattr(status.module, "STATSMODELS_AVAILABLE", False):
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": "statsmodels and scipy are required for StructuralCausalAnalyzer.",
                "adapter_id": "A-12-SCM",
            }

        adapter_fn = getattr(status.module, "adapter_structural_causal", None)
        if adapter_fn is None:
            return {
                "validated": False,
                "status": "invalid_legacy_module",
                "error": "adapter_structural_causal not found in legacy structural_causal module",
                "adapter_id": "A-12-SCM",
            }

        try:
            return adapter_fn(data, params)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
                "adapter_id": "A-12-SCM",
            }

    def run_causal_emergence(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        status = self.status("complex_systems_adapters")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "complex_systems_adapters unavailable",
                "adapter_id": "A-18",
            }

        adapter_cls = getattr(status.module, "CausalEmergenceAdapter", None)
        if adapter_cls is None:
            return {
                "validated": False,
                "status": "invalid_legacy_module",
                "error": "CausalEmergenceAdapter not found in legacy complex_systems_adapters module",
                "adapter_id": "A-18",
            }

        try:
            return adapter_cls()(data=data, params=params)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
                "adapter_id": "A-18",
            }

    def run_network_science(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        status = self.status("network_science_adapters")
        if not status.available or status.module is None:
            return self._run_network_fallback(data, params, status.error)

        adapter_cls = getattr(status.module, "NetworkScienceAdapter", None)
        if adapter_cls is None:
            return self._run_network_fallback(data, params, "NetworkScienceAdapter not found in legacy module")

        normalized = dict(data)
        if "adjacency_matrix" not in normalized and "adjacency" in normalized:
            normalized["adjacency_matrix"] = normalized["adjacency"]

        try:
            return adapter_cls()(data=normalized, params=params)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
                "adapter_id": "A-22",
            }

    def _run_network_fallback(self, data: Dict[str, Any], params: Dict[str, Any], error: Optional[str]) -> Dict[str, Any]:
        analysis = params.get("analysis", "percolation")
        adjacency = data.get("adjacency_matrix", data.get("adjacency"))
        adjacency = np.asarray(adjacency if adjacency is not None else [], dtype=float)
        if adjacency.ndim != 2:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": error or "network_science_adapters unavailable",
                "adapter_id": "A-22",
            }

        if analysis == "pagerank":
            return self._network_pagerank_fallback(adjacency, params, error)
        if analysis == "percolation":
            return self._network_percolation_fallback(adjacency, params, error)
        if analysis == "cascade":
            return self._network_cascade_fallback(adjacency, params, error)
        if analysis == "sir_network":
            return self._network_sir_fallback(adjacency, params, error)
        return {
            "validated": False,
            "status": "dependency_unavailable",
            "error": error or f"No fallback available for network analysis type {analysis}",
            "adapter_id": "A-22",
        }

    def _network_pagerank_fallback(self, adjacency: np.ndarray, params: Dict[str, Any], error: Optional[str]) -> Dict[str, Any]:
        n = adjacency.shape[0]
        damping = float(params.get("damping", 0.85))
        tol = float(params.get("tolerance", 1e-6))
        out_degree = np.sum(adjacency, axis=0)
        matrix = np.divide(adjacency, out_degree, out=np.zeros_like(adjacency, dtype=float), where=out_degree > 0)

        pr = np.ones(n) / n
        for _ in range(1000):
            new_pr = (1 - damping) / n + damping * matrix @ pr
            if np.linalg.norm(new_pr - pr, 1) < tol:
                pr = new_pr
                break
            pr = new_pr

        top_indices = np.argsort(pr)[::-1][: min(5, n)]
        top_nodes = [{"node": int(i), "pagerank": round(float(pr[i]), 6)} for i in top_indices]
        gini = self._gini_coefficient(pr)
        result = {
            "analysis": "pagerank",
            "causal_grade": "C1",
            "causal_note": "PageRank measures influence but not intervention causality.",
            "n_nodes": n,
            "top_influencers": top_nodes,
            "gini_coefficient": round(float(gini), 4),
            "network_centrality": "CONCENTRATED" if gini > 0.5 else "DISTRIBUTED",
            "interpretation": f"Fallback PageRank executed with top node {top_nodes[0]['node']}.",
            "validated": True,
            "adapter_id": "A-22-NETWORK",
            "status": "fallback_executed",
        }
        if error:
            result["warning"] = f"Legacy adapter unavailable, used numpy fallback: {error}"
        return result

    def _network_percolation_fallback(self, adjacency: np.ndarray, params: Dict[str, Any], error: Optional[str]) -> Dict[str, Any]:
        n = adjacency.shape[0]
        n_removals = int(params.get("n_removals", min(max(n - 1, 1), 50)))
        n_trials = int(params.get("n_trials", 25))
        fractions = np.linspace(0, 0.8, n_removals)
        gcc_sizes = []
        np.random.seed(42)
        for f in fractions:
            sizes = []
            for _ in range(n_trials):
                keep = np.random.random(n) > f
                if np.sum(keep) == 0:
                    sizes.append(0.0)
                    continue
                sub_adj = adjacency[np.ix_(keep, keep)]
                gcc = self._largest_component_size(sub_adj)
                sizes.append(gcc / np.sum(keep))
            gcc_sizes.append(float(np.mean(sizes)))
        gcc_sizes_arr = np.asarray(gcc_sizes)
        critical_idx = np.where(gcc_sizes_arr < 0.5)[0]
        fc = float(fractions[critical_idx[0]]) if len(critical_idx) > 0 else 1.0
        result = {
            "analysis": "percolation",
            "causal_grade": "C1",
            "causal_note": "Percolation threshold is an emergent connectivity property.",
            "network_size": n,
            "critical_threshold_fc": round(fc, 4),
            "robustness": "ROBUST" if fc > 0.5 else "FRAGILE",
            "validated": True,
            "adapter_id": "A-22-NETWORK",
            "status": "fallback_executed",
        }
        if error:
            result["warning"] = f"Legacy adapter unavailable, used numpy fallback: {error}"
        return result

    def _network_cascade_fallback(self, adjacency: np.ndarray, params: Dict[str, Any], error: Optional[str]) -> Dict[str, Any]:
        n = adjacency.shape[0]
        degree = np.sum(adjacency > 0, axis=1)
        capacity_factor = float(params.get("capacity_factor", 1.5))
        capacity = degree.astype(float) * capacity_factor
        initial_failures = [int(np.argmax(degree))]
        failed = set(initial_failures)
        round_num = 0
        while True:
            round_num += 1
            new_failures = set()
            remaining = [i for i in range(n) if i not in failed]
            if len(remaining) < 2:
                break
            sub_adj = adjacency[np.ix_(remaining, remaining)]
            sub_degree = np.sum(sub_adj > 0, axis=1)
            if np.sum(sub_degree) == 0:
                break
            for idx, node in enumerate(remaining):
                if sub_degree[idx] > capacity[node]:
                    new_failures.add(node)
            if not new_failures:
                break
            failed.update(new_failures)
            if round_num > n:
                break
        cascade_ratio = len(failed) / max(n, 1)
        result = {
            "analysis": "cascading_failure",
            "causal_grade": "C1",
            "causal_note": "Cascade is an emergent failure propagation process.",
            "initial_attack_nodes": initial_failures,
            "capacity_factor": capacity_factor,
            "cascade_rounds": round_num,
            "total_failed": len(failed),
            "cascade_ratio": round(float(cascade_ratio), 4),
            "validated": True,
            "adapter_id": "A-22-NETWORK",
            "status": "fallback_executed",
        }
        if error:
            result["warning"] = f"Legacy adapter unavailable, used numpy fallback: {error}"
        return result

    def _network_sir_fallback(self, adjacency: np.ndarray, params: Dict[str, Any], error: Optional[str]) -> Dict[str, Any]:
        n = adjacency.shape[0]
        beta = float(params.get("beta", 0.3))
        gamma = float(params.get("gamma", 0.1))
        n_steps = int(params.get("n_steps", 50))
        n_trials = int(params.get("n_trials", 20))
        np.random.seed(42)
        peak_infections = []
        final_attack_ratios = []
        for _ in range(n_trials):
            susceptible = np.ones(n)
            infected = np.zeros(n)
            recovered = np.zeros(n)
            patient_zero = np.random.randint(n)
            susceptible[patient_zero] = 0
            infected[patient_zero] = 1
            infections_over_time = []
            for _ in range(n_steps):
                new_infections = np.zeros(n)
                new_recoveries = np.zeros(n)
                for node in np.where(infected == 1)[0]:
                    neighbors = np.where(adjacency[node] > 0)[0]
                    for nb in neighbors:
                        if susceptible[nb] == 1 and np.random.random() < beta:
                            new_infections[nb] = 1
                    if np.random.random() < gamma:
                        new_recoveries[node] = 1
                susceptible = susceptible * (1 - new_infections)
                infected = infected * (1 - new_recoveries) + new_infections
                recovered = recovered + new_recoveries
                infections_over_time.append(np.sum(infected))
            peak_infections.append(float(np.max(infections_over_time)))
            final_attack_ratios.append(float(np.sum(recovered) / max(n, 1)))
        result = {
            "analysis": "sir_network",
            "causal_grade": "C1",
            "causal_note": "Network structure modifies epidemic spread dynamics.",
            "network_size": n,
            "beta": beta,
            "gamma": gamma,
            "r0_effective": round(float(beta / gamma), 4),
            "peak_infection_mean": round(float(np.mean(peak_infections)), 4),
            "final_attack_ratio": round(float(np.mean(final_attack_ratios)), 4),
            "validated": True,
            "adapter_id": "A-22-NETWORK",
            "status": "fallback_executed",
        }
        if error:
            result["warning"] = f"Legacy adapter unavailable, used numpy fallback: {error}"
        return result

    @staticmethod
    def _largest_component_size(adj: np.ndarray) -> int:
        n = adj.shape[0]
        visited = np.zeros(n, dtype=bool)
        max_size = 0
        for i in range(n):
            if visited[i]:
                continue
            size = 0
            stack = [i]
            visited[i] = True
            while stack:
                node = stack.pop()
                size += 1
                for nb in np.where(adj[node] > 0)[0]:
                    if not visited[nb]:
                        visited[nb] = True
                        stack.append(int(nb))
            max_size = max(max_size, size)
        return max_size

    @staticmethod
    def _gini_coefficient(values: np.ndarray) -> float:
        x = np.sort(values)
        n = len(x)
        cumsum = np.cumsum(x)
        return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0.0

    def run_abm(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        status = self.status("abm_adapter_v450")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "abm_adapter_v450 unavailable",
                "adapter_id": "A-23",
            }

        adapter_cls = getattr(status.module, "ABMAdapter", None)
        if adapter_cls is None:
            return {
                "validated": False,
                "status": "invalid_legacy_module",
                "error": "ABMAdapter not found in legacy abm_adapter_v450 module",
                "adapter_id": "A-23",
            }

        try:
            return adapter_cls()(data=data, params=params)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
                "adapter_id": "A-23",
            }

    def run_cusum_with_rigor(
        self,
        data: Any,
        change_indices: list[int],
        *,
        n_boot: int = 1000,
        block_len: Optional[int] = None,
        fdr_alpha: float = 0.05,
        seed: int = 42,
    ) -> Dict[str, Any]:
        status = self.status("statistical_rigor")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "statistical_rigor unavailable",
            }

        return status.module.cusum_with_rigor(
            data,
            change_indices,
            n_boot=n_boot,
            block_len=block_len,
            fdr_alpha=fdr_alpha,
            seed=seed,
        )

    def upgrade_causal(
        self,
        granger_result: Dict[str, Any],
        scm_result: Optional[Dict[str, Any]] = None,
        *,
        cause: str = "",
        effect: str = "",
    ) -> Dict[str, Any]:
        status = self.status("statistical_rigor")
        if not status.available or status.module is None:
            return {
                "cause": cause,
                "effect": effect,
                "granger": granger_result,
                "scm": scm_result,
                "final_grade": "C1",
                "recommendation": f"Upgrade unavailable: {status.error or 'statistical_rigor missing'}",
            }
        return status.module.upgrade_causal(
            granger_result,
            scm_result,
            cause=cause,
            effect=effect,
        )

    def run_granger(
        self,
        y: Any,
        x: Any,
        *,
        lags: int = 2,
        make_stationary: bool = True,
    ) -> Dict[str, Any]:
        status = self.status("stats_module")
        if not status.available or status.module is None:
            return {
                "validated": False,
                "status": "dependency_unavailable",
                "error": status.error or "stats_module unavailable",
            }

        tester_cls = getattr(status.module, "CausalityTester", None)
        if tester_cls is None:
            return {
                "validated": False,
                "status": "invalid_legacy_module",
                "error": "CausalityTester not found in legacy stats_module",
            }

        try:
            tester = tester_cls()
            return tester.granger(y, x, lags=lags, make_stationary=make_stationary)
        except Exception as exc:
            return {
                "validated": False,
                "status": "execution_failed",
                "error": str(exc),
            }
