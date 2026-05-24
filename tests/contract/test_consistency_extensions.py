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


def test_scan_wide_percentage_conflict_within_short_snippet() -> None:
    sigs = consistency.scan_wide_percentage_conflict_within_blocks(["cpu 10% idle and 72% utilization in same window"])
    assert any("wide_percentage_spread_inside_single_snippet" in s for s in sigs)
    assert any("percents_seen=" in s for s in sigs)


def test_scan_mutex_resolution_tokens_ipc_short_blob() -> None:
    blob = "Substream defaults to 720p while mainstream advertises 1080p encoder block"
    sigs = consistency.scan_mutex_video_resolution_tokens([blob])
    assert any("mutex_video_resolution_tokens_single_snippet_ipc_review" in s for s in sigs)


def test_scan_competing_latency_ms_ipc_short_blob() -> None:
    blob = "End-to-end claim 45 ms yet measured glass-to-glass 310 ms without network scope"
    sigs = consistency.scan_competing_latency_ms_claims([blob])
    assert any("competing_latency_ms_narratives_in_short_snippet" in s for s in sigs)


def test_scan_onvif_proprietary_mutex_language() -> None:
    blob = "Device markets ONVIF discovery while shipping a vendor-locked provisioning stack only"
    sigs = consistency.scan_onvif_proprietary_mutex_language([blob])
    assert any("onvif_vs_proprietary_mutex_language_ipc_review" in s for s in sigs)
