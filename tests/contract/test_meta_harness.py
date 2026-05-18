from pyc_hermes_agent.contracts import MetaAnalysisRequest
from pyc_hermes_agent.meta_harness import MetaFramework


def test_meta_framework_selects_scm_for_causal_request() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="因果分析：X 对 Y 的影响"))
    assert result.selected_method == "A-12-SCM"
    assert result.evidence_grade == "CE-C3"
    assert result.degraded is False


def test_meta_framework_degrades_on_unknown_request() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="please do something vague"))
    assert result.degraded is True
    assert result.selected_method == "manual-review"


def test_meta_framework_selects_team_method_for_team_request() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="团队冲突与生产力分析"))
    assert result.selected_method == "A-15"
    assert any("org_personal_adapters" in note for note in result.risks)


def test_meta_framework_selects_forecast_when_series_present() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="forecast weekly orders",
            data={"series": [10.0, 12.0, 11.5]},
        )
    )
    assert result.selected_method == "A-12-FORECAST"


def test_meta_framework_does_not_select_network_without_graph_payload() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="network pagerank discussion only"))
    assert result.selected_method != "A-22"


def test_meta_framework_flags_overclaimed_certainty_in_risks() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="proved causation with certainty"))
    assert any("certainty" in note.lower() or "over-claim" in note.lower() for note in result.risks)


def test_meta_framework_selects_network_method_from_data_shape() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="analyze influence structure",
            data={"adjacency": [[0, 1], [1, 0]]},
        )
    )
    assert result.selected_method == "A-22"


def test_meta_framework_reports_dependency_availability_snapshot() -> None:
    framework = MetaFramework()

    snapshot = framework.dependency_snapshot()

    assert snapshot["entrypoint"] == "MetaFramework.execute"
    assert snapshot["capability_count"] >= 1
    assert any(capability["id"] == "A-22" for capability in snapshot["capabilities"])
    network = next(capability for capability in snapshot["capabilities"] if capability["id"] == "A-22")
    assert network["dependencies"][0]["name"] == "network_science_adapters"
    assert "available" in network["dependencies"][0]


def test_meta_framework_runs_benchmark_smoke_through_execute() -> None:
    framework = MetaFramework()

    smoke = framework.run_benchmark_smoke()

    assert smoke["entrypoint"] == "MetaFramework.execute"
    assert smoke["case_count"] == 6
    assert smoke["passed"] is True
    assert smoke["failed_count"] == 0
    assert any(case["selected_method"] == "A-22" for case in smoke["cases"])
    assert any(case["selected_method"] == "A-12-FORECAST" for case in smoke["cases"])
    assert all(case["duration_ms"] >= 0 for case in smoke["cases"])
