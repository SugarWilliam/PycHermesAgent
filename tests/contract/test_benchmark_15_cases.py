"""Contract test for the 15-case external MetaHarness benchmark."""

from __future__ import annotations

import sys
import pathlib

# Ensure benchmarks package is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "benchmarks"))

from benchmarks.meta_harness.run_benchmark import run_benchmark  # noqa: E402


class TestBenchmark15Cases:
    def test_benchmark_passes(self) -> None:
        report = run_benchmark()
        assert report["passed"] is True, (
            f"MetaHarness won {report['metrics_won']}/4 metrics (need >=3)"
        )

    def test_all_15_cases_evaluated(self) -> None:
        report = run_benchmark()
        assert report["case_count"] == 15

    def test_wins_at_least_3_metrics(self) -> None:
        report = run_benchmark()
        assert report["metrics_won"] >= 3, (
            f"Won {report['metrics_won']} metrics: "
            f"{[(k, v['score']) for k, v in report['metrics'].items()]}"
        )
