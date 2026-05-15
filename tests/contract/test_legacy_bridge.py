from pathlib import Path

import numpy as np

from pyc_hermes_agent.contracts import MetaAnalysisRequest
from pyc_hermes_agent.meta_harness import MetaFramework
from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge


def test_legacy_bridge_finds_infrastructure_root() -> None:
    bridge = LegacyMetaBridge()
    assert bridge.legacy_root.exists()
    assert bridge.legacy_root.name == "核心基础设施"


def test_statistical_rigor_bridge_executes_without_optional_scipy_stack() -> None:
    bridge = LegacyMetaBridge()
    data = np.concatenate([np.zeros(20), np.ones(20)])
    result = bridge.run_cusum_with_rigor(data, [20], n_boot=50, seed=42)
    assert result["n_candidate"] == 1
    assert "report_str" in result


def test_stats_module_bridge_reports_dependency_error() -> None:
    bridge = LegacyMetaBridge()
    result = bridge.run_granger(np.arange(10.0), np.arange(10.0), lags=2)
    assert result["validated"] is False
    assert result["status"] == "dependency_unavailable"


def test_forecast_execution_degrades_cleanly_when_dependencies_are_missing() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="forecast the next values of this time series",
            data={"series": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
            params={"horizon": 2},
        )
    )
    assert result.selected_method == "A-12-FORECAST"
    assert result.degraded is True
    assert result.execution_details["adapter_id"] == "A-12-FORECAST"


def test_scm_execution_degrades_cleanly_when_dependencies_are_missing() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="因果分析 X 对 Y 的影响",
            data={"df": object(), "cause": "x", "effect": "y"},
            params={"method": "auto"},
        )
    )
    assert result.selected_method == "A-12-SCM"
    assert result.degraded is True
    assert result.execution_details["adapter_id"] == "A-12-SCM"
