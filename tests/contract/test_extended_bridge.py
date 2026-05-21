import numpy as np

from pyc_hermes_agent.contracts import MetaAnalysisRequest
from pyc_hermes_agent.meta_harness import MetaFramework
from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge


def test_network_bridge_executes_with_numpy_only() -> None:
    bridge = LegacyMetaBridge()
    result = bridge.run_network_science(
        {"adjacency": np.array([[0.0, 1.0], [1.0, 0.0]])},
        {"analysis": "pagerank"},
    )
    assert result["validated"] is True
    assert result["adapter_id"] == "A-22-NETWORK"


def test_abm_bridge_executes_with_numpy_only() -> None:
    bridge = LegacyMetaBridge()
    result = bridge.run_abm({}, {"model": "schelling", "grid_size": 10, "n_agents": 40, "n_steps": 10})
    assert result["validated"] is True
    assert result["adapter_id"] == "A-23-ABM"


def test_complex_bridge_degrades_when_scipy_stack_is_missing() -> None:
    bridge = LegacyMetaBridge()
    result = bridge.run_causal_emergence({"micro_states": np.random.randint(0, 8, size=120)}, {})
    assert result["validated"] is False
    assert result["status"] == "dependency_unavailable"


def test_org_bridge_degrades_when_pandas_stack_is_missing() -> None:
    bridge = LegacyMetaBridge()
    result = bridge.run_organization(
        {"planned_value": [1, 2, 3], "earned_value": [1, 2, 3], "actual_cost": [1, 2, 3]},
        {"analysis": "evm", "budget_at_completion": 10},
    )
    assert result["validated"] is False
    assert result["status"] == "dependency_unavailable"


def test_meta_framework_executes_network_path() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="network pagerank analysis",
            data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            params={"analysis": "pagerank"},
        )
    )
    assert result.selected_method == "A-22"
    assert result.degraded is False
    assert result.execution_details["validated"] is True
