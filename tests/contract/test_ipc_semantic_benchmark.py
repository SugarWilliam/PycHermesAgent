"""Contract checks for Phase 3F IPC business MRAG benchmark."""

from __future__ import annotations


def test_ipc_semantic_business_benchmark_passes() -> None:
    from benchmarks.mrag.ipc_semantic_benchmark import assert_ipc_business_benchmark_passes

    assert_ipc_business_benchmark_passes()

