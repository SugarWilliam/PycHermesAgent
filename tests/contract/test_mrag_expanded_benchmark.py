"""Phase 3F — expanded lexical vs hybrid benchmark (offline, deterministic)."""

from __future__ import annotations

from benchmarks.mrag.expanded_benchmark import run_expanded_benchmark


def test_expanded_mr_ag_benchmark_all_scenarios_swap_top1() -> None:
    exit_code, lines = run_expanded_benchmark()
    assert exit_code == 0, "\n".join(lines)
    assert lines and lines[0].startswith("OK expanded MRAG benchmark")
