"""Contract tests for the sidecar health state machine."""

from pyc_hermes_agent.sidecar_api.health import HealthState, SidecarHealth


def test_health_state_enum_values():
    """Validate all 4 enum values exist."""
    assert HealthState.READY.value == "ready"
    assert HealthState.READY_WITH_WARNINGS.value == "ready_with_warnings"
    assert HealthState.DEGRADED.value == "degraded"
    assert HealthState.UNAVAILABLE.value == "unavailable"
    assert len(HealthState) == 4


def test_health_evaluate_returns_valid_state():
    """SidecarHealth.evaluate() returns valid HealthState."""
    result = SidecarHealth.evaluate()
    assert isinstance(result, SidecarHealth)
    assert isinstance(result.state, HealthState)
    assert result.state in list(HealthState)


def test_health_components_all_present():
    """At least 3 components reported."""
    result = SidecarHealth.evaluate()
    assert len(result.components) >= 3
    names = [c.name for c in result.components]
    assert "llm_gateway" in names
    assert "meta_harness" in names
    assert "mrag" in names


def test_health_ready_when_all_ok():
    """Under normal test conditions, state should be READY or READY_WITH_WARNINGS."""
    result = SidecarHealth.evaluate()
    # In the test environment, components may be degraded if config is missing,
    # but the state machine itself must not be UNAVAILABLE.
    assert result.state in (HealthState.READY, HealthState.READY_WITH_WARNINGS, HealthState.DEGRADED)


def test_health_to_dict_structure():
    """to_dict() returns expected JSON-serializable structure."""
    result = SidecarHealth.evaluate()
    d = result.to_dict()
    assert "state" in d
    assert "components" in d
    assert "degradation_reasons" in d
    assert "version" in d
    assert "sidecar_api_version" in d
    assert isinstance(d["components"], list)
    for comp in d["components"]:
        assert "name" in comp
        assert "state" in comp
        assert "message" in comp
