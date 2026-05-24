"""Deterministic IPC / ONVIF-style MRAG contrast pairs (Phase 3F business corpus)."""

from __future__ import annotations

from benchmarks.mrag.expanded_benchmark import ScenarioSpec, ingest_scenario_corpus, scenario_top1_differs_lex_hybrid

from pyc_hermes_agent.mrag_core import MRAGService

IPC_BUSINESS_SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        key="onvif_ivs_tripwire_token_split",
        doc_lex_hits=[
            "ONVIF Profile S checklist RTSP TCP UDP port matrix DHCP DNS NTP syslog baseline security bulletin "
            "generic audit logging rotation east west north south filler baseline compliance paragraph tail"
        ],
        doc_sem_aligned=[
            "zzz ipcIVSIntrusionTripwireRare token cluster zzz harmonic tripwire rareTripwireTrigram zzz "
            "IVS line-crossing analytics zzz ipcIVSIntrusionTripwireRare duplicate rareTripwireTrigram tail"
        ],
        query="ONVIF RTSP ipcIVSIntrusionTripwireRare",
        hybrid_sem_weight=0.66,
        topical_k_overview=[
            "warehouse pallet inventory generic safety document",
            "holiday firmware blackout maintenance noise text",
        ],
    ),
    ScenarioSpec(
        key="h265_bitrate_lex_vs_sensor_sem",
        doc_lex_hits=[
            "H265 H264 GOP I-frame P-frame baseline encoder settings CBR VBR firmware release notes placeholder "
            "generic surveillance paragraph filler compliance checklist matrix tail section boilerplate"
        ],
        doc_sem_aligned=[
            "zzz rareThermalDriftSensorToken zzz harmonic thermal drift calibration zzz rareThermalDriftSensorToken "
            "corpus repetition zzz sensor fusion metadata zzz rareThermalDriftSensorToken harmonic block"
        ],
        query="H265 CBR rareThermalDriftSensorToken",
        hybrid_sem_weight=0.7,
        topical_k_overview=[
            "office HVAC maintenance generic policy",
            "shipping dock camera placement generic guidance",
        ],
    ),
    ScenarioSpec(
        key="sip_pts_door_station_token_split",
        doc_lex_hits=[
            "SIP SDP RTP TCP UDP QoS jitter buffer syslog generic release notes VLAN trunk matrix baseline "
            "compliance filler paragraph interoperability checklist appendix tail boilerplate surveillance"
        ],
        doc_sem_aligned=[
            "zzz rarePtsVillaDoorRareToken zzz harmonic PTS doorstation audio routing zzz rarePtsVillaDoorRareToken "
            "villa intercom two-wire lift zzz rarePtsVillaDoorRareToken harmonic duplicate tail"
        ],
        query="SIP SDP rarePtsVillaDoorRareToken",
        hybrid_sem_weight=0.72,
        topical_k_overview=[
            "retail storefront generic WIFI planning doc",
            "parking barrier gate signage maintenance notice",
        ],
    ),
    ScenarioSpec(
        key="aac_echo_cancel_lex_vs_ipc_sem",
        doc_lex_hits=[
            "AAC PCM G711 G726 sample rate opus encoder firmware audio pipeline generic datasheet paragraph "
            "compliance filler matrix baseline RTSP onboarding boilerplate appendix tail surveillance"
        ],
        doc_sem_aligned=[
            "zzz rareIntercomAecLeakToken zzz harmonic full-duplex AEC leakage guard zzz rareIntercomAecLeakToken "
            "duplex tails near-end zzz rareIntercomAecLeakToken harmonic block duplicate"
        ],
        query="AAC G711 rareIntercomAecLeakToken",
        hybrid_sem_weight=0.67,
        topical_k_overview=[
            "factory floor paging generic safety briefing",
            "warehouse forklift traffic camera placement notes",
        ],
    ),
)


def run_ipc_business_benchmark(
    *,
    scenarios: tuple[ScenarioSpec, ...] = IPC_BUSINESS_SCENARIOS,
) -> tuple[int, list[str]]:
    failures = 0
    lines: list[str] = []
    for spec in scenarios:
        svc = MRAGService()
        kb = svc.create_knowledge_base(f"ipc-business-{spec.key}")
        ingest_scenario_corpus(svc, kb.knowledge_base_id, spec)
        ok, lx, hh = scenario_top1_differs_lex_hybrid(svc, kb.knowledge_base_id, spec)
        lines.append(f"{'OK' if ok else 'FAIL'} scenario={spec.key} lexical_top={lx} hybrid_top={hh}")
        if not ok:
            failures += 1
    return failures, lines


def assert_ipc_business_benchmark_passes() -> None:
    failures, lines = run_ipc_business_benchmark()
    if failures:
        detail = "\n".join(lines)
        raise RuntimeError(f"ipc business benchmark failed ({failures} scenarios)\n{detail}")


__all__ = ["IPC_BUSINESS_SCENARIOS", "assert_ipc_business_benchmark_passes", "run_ipc_business_benchmark"]
