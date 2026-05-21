from pyc_hermes_agent.hermes_engine import find_capability_mapping, get_mixed_integration_plan


def test_mixed_integration_plan_uses_mixed_strategy() -> None:
    plan = get_mixed_integration_plan()

    assert plan.strategy == "mixed"
    assert plan.mappings


def test_mapping_freezes_core_hermes_ownership_decisions() -> None:
    session_store = find_capability_mapping("hermes.sessions.store")
    orchestration = find_capability_mapping("hermes.orchestration.loop")
    skills_runtime = find_capability_mapping("hermes.skills.runtime")
    gateway_platforms = find_capability_mapping("hermes.gateway.platforms")

    assert session_store is not None
    assert session_store.target_owner == "hermes_engine"
    assert session_store.integration_mode == "deep-bridge"

    assert orchestration is not None
    assert orchestration.integration_mode == "rebuild"
    assert orchestration.target_module == "hermes_engine.agent_loop"

    assert skills_runtime is not None
    assert skills_runtime.target_owner == "llm_gateway"
    assert skills_runtime.integration_mode == "rebuild"

    assert gateway_platforms is not None
    assert gateway_platforms.integration_mode == "subprocess-readonly"
    assert gateway_platforms.status == "deferred"


def test_mapping_keeps_run_agent_out_of_product_runtime_embedding() -> None:
    orchestration = find_capability_mapping("hermes.orchestration.loop")

    assert orchestration is not None
    assert "run_agent.py" in orchestration.upstream_paths
    assert "Do not embed run_agent.py as the product runtime." in orchestration.notes
