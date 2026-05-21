from pyc_hermes_agent.meta_harness.benchmark import run_value_proof_benchmark


def test_value_proof_benchmark_passes_fixed_scenarios() -> None:
    report = run_value_proof_benchmark()
    assert report["entrypoint"] == "MetaFramework.execute"
    assert report["benchmark_id"] == "meta_harness.value_proof.v1"
    assert report["scenario_count"] == 4
    assert report["passed"] is True
    agg = report["aggregate"]
    assert agg["guided_overclaim_detection_cases"] >= 1
    assert agg["graph_routes_a22_cases"] == 1
    assert agg["dependency_risk_surface_cases"] == 1
    assert any(row["signals"]["guided_flags_overclaim_vs_baseline_silent"] for row in report["cases"])


def test_baseline_stub_has_no_structured_risks() -> None:
    from pyc_hermes_agent.contracts import MetaAnalysisRequest
    from pyc_hermes_agent.meta_harness.benchmark.value_proof import baseline_llm_stub

    stub = baseline_llm_stub(MetaAnalysisRequest(problem_statement="proved causation with certainty"))
    assert stub["structured_risks"] == []
    assert stub["user_prompt_has_overclaim_language"] is True
