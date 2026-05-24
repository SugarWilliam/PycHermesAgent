"""Phase 3F consistency scan extensions."""

from __future__ import annotations

from pyc_hermes_agent.meta_harness import consistency


def test_scan_relative_time_signals_detects_last_week() -> None:
    sigs = consistency.scan_relative_time_signals("", ["we shipped last week with no timestamp"])
    assert sigs


def test_scan_version_literal_density_flags_many_versions() -> None:
    blob = " ".join([f"firmware {i}.0.0" for i in range(1, 5)])
    sigs = consistency.scan_version_literal_density([blob])
    assert sigs
