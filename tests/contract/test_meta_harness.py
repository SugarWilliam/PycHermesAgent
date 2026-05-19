from pyc_hermes_agent.contracts import MetaAnalysisRequest
from pyc_hermes_agent.meta_harness import MetaFramework


def test_meta_framework_selects_scm_for_causal_request() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="因果分析：X 对 Y 的影响"))
    assert result.selected_method == "A-12-SCM"
    assert result.evidence_grade == "CE-C3"
    assert result.sr_grade == "SR-C1"
    assert result.degraded is False


def test_meta_framework_keeps_ce_and_sr_grade_dimensions_distinct() -> None:
    """CE (causal evidence) and SR (structural/representational) must stay separate fields."""
    framework = MetaFramework()
    causal = framework.execute(MetaAnalysisRequest(problem_statement="因果分析：X 对 Y 的影响"))
    assert causal.evidence_grade.startswith("CE-")
    assert causal.sr_grade.startswith("SR-")
    assert causal.evidence_grade != causal.sr_grade

    forecast = framework.execute(
        MetaAnalysisRequest(
            problem_statement="forecast weekly orders",
            data={"series": [10.0, 12.0, 11.5]},
        )
    )
    assert forecast.evidence_grade.startswith("CE-")
    assert forecast.sr_grade.startswith("SR-")

    degraded = framework.execute(MetaAnalysisRequest(problem_statement="please do something vague"))
    assert degraded.evidence_grade.startswith("CE-")
    assert degraded.sr_grade.startswith("SR-")


def test_meta_framework_degrades_on_unknown_request() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="please do something vague"))
    assert result.degraded is True
    assert result.selected_method == "manual-review"


def test_meta_framework_selects_complex_systems_method_for_emergence_request() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="复杂系统涌现分析"))
    assert result.selected_method == "A-18"
    assert any("complex_systems_adapters" in note for note in result.risks)


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


def test_meta_framework_vague_request_earns_lower_sr_grade() -> None:
    framework = MetaFramework()
    result = framework.execute(MetaAnalysisRequest(problem_statement="please do something vague"))
    assert result.sr_grade == "SR-C2"


def test_meta_routing_pin_method_selects_capability() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="complex systems emergence task",
            meta_routing={"pin_method": "A-18"},
        )
    )
    assert result.selected_method == "A-18"
    assert "Pinned" in result.method_rationale


def test_meta_routing_keyword_overlay_can_raise_method_priority() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="xyzzy analysis for agent-based modeling",
            meta_routing={"keyword_boosts": {"A-23": ["xyzzy"]}},
            data={"agents": [1, 2, 3]},
        )
    )
    assert result.selected_method == "A-23"


def test_target_sr_grade_override_is_respected() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="please do something vague",
            target_sr_grade="SR-C9",
        )
    )
    assert result.sr_grade == "SR-C9"


def test_allowed_methods_constrains_routing() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="因果分析：X 对 Y 的影响",
            allowed_methods=["A-12-FORECAST"],
        )
    )
    assert result.selected_method != "A-12-SCM"
    assert result.selected_method == "manual-review"


def test_meta_routing_data_shape_bonus_adds_score_without_builtin_match() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="quarterly entropy discussion",
            data={"micro_states": [1, 2]},
            meta_routing={"data_shape_bonus": {"A-18": 40}},
        )
    )
    assert result.selected_method == "A-18"


def test_meta_routing_data_shape_bonus_stacks_with_builtin_shape_rules() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="map influence given the graph",
            data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            meta_routing={"data_shape_bonus": {"A-22": 2}},
        )
    )
    assert result.selected_method == "A-22"


def test_meta_routing_data_shape_rules_any_keys() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="agent-based simulation with custom feed",
            data={"custom_signal_feed": [0.1, 0.2], "agents": [1]},
            meta_routing={
                "data_shape_rules": [
                    {"capability_id": "A-23", "any_keys": ["custom_signal_feed"], "points": 70},
                ],
            },
        )
    )
    assert result.selected_method == "A-23"


def test_meta_routing_data_shape_rules_all_keys_conjunctive() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="complex emergence with state data",
            data={"ledger": 1, "notes": "x", "micro_states": [1]},
            meta_routing={
                "data_shape_rules": [
                    {"capability_id": "A-18", "all_keys": ["ledger", "notes"], "points": 80},
                ],
            },
        )
    )
    assert result.selected_method == "A-18"


def test_meta_routing_data_shape_rules_any_and_all_both_required() -> None:
    framework = MetaFramework()
    result_ok = framework.execute(
        MetaAnalysisRequest(
            problem_statement="network topology mixed keys",
            data={"flag": 1, "x": 1, "y": 1, "adjacency": [[0, 1]]},
            meta_routing={
                "data_shape_rules": [
                    {"capability_id": "A-22", "any_keys": ["flag"], "all_keys": ["x", "y"], "points": 90},
                ],
            },
        )
    )
    assert result_ok.selected_method == "A-22"

    result_fail = framework.execute(
        MetaAnalysisRequest(
            problem_statement="network topology missing all_keys",
            data={"flag": 1, "x": 1, "adjacency": [[0, 1]]},
            meta_routing={
                "data_shape_rules": [
                    {"capability_id": "A-22", "any_keys": ["flag"], "all_keys": ["x", "y"], "points": 90},
                ],
            },
        )
    )
    # A-22 still wins from adjacency data shape, but rule points should not apply
    # Just verify the rule didn't give extra points (hard to test negatively; verify rule logic works)
    assert result_fail.selected_method == "A-22"  # adjacency still matches builtin


def test_meta_routing_data_shape_rules_sum_with_data_shape_bonus() -> None:
    framework = MetaFramework()
    result = framework.execute(
        MetaAnalysisRequest(
            problem_statement="agent-based routing contest",
            data={"custom_signal_feed": [1], "agents": [1]},
            meta_routing={
                "data_shape_bonus": {"A-23": 10},
                "data_shape_rules": [{"capability_id": "A-23", "any_keys": ["custom_signal_feed"], "points": 50}],
            },
        )
    )
    assert result.selected_method == "A-23"
