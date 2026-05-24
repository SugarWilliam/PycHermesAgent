"""Reserved Agent-to-Agent (A2A) / sub-agent seam — contract-only in Phase v0.4."""

from __future__ import annotations

from typing import Any

# Stable public identifier for this repository's future A2A profile (not interoperable beyond docs yet).
A2A_PROTOCOL_ID: str = "pyc-hermes-a2a"
# Semantic version for the JSON surface returned by GET /capabilities/a2a.
A2A_PROTOCOL_VERSION: str = "0.1.0"


def build_a2a_capability_document(*, sidecar_api_version: str) -> dict[str, Any]:
    """Advertise intentionally narrow, forward-compatible hooks.

    Boundary: orchestration stays in ``hermes_engine``; harness stays in ``meta_harness``.
    Peer agents never receive provider SDK blobs — only negotiated JSON envelopes (future).
    """

    return {
        "schema": "pyc-hermes.agent.a2a.capability_document.v1",
        "a2a_protocol_id": A2A_PROTOCOL_ID,
        "a2a_protocol_version": A2A_PROTOCOL_VERSION,
        "implementation_maturity": "reserved_future",
        "sidecar_api_version": sidecar_api_version,
        "notes": (
            "This document reserves names and versioning axes for eventual sub-agent delegation, "
            "peer discovery, and cross-runtime handoff. No A2A traffic is negotiated by this release."
        ),
        "recommended_next_steps": [
            "Freeze transport (HTTPS + optional mTLS), capability advertisement, and task correlation IDs.",
            "Add optional POST /a2a/tasks (delegation envelope) guarded by explicit policy + audit.",
            "Mirror desktop preload bridge with least-privilege IPC contracts.",
        ],
        "reserved_future_http_endpoints": [
            {"method": "POST", "path": "/a2a/handoff/reserve", "purpose": "Sub-agent delegation envelope ingestion (stub)."},
            {"method": "POST", "path": "/a2a/telemetry/reserve", "purpose": "Peer agent observability sinks (stub)."},
        ],
        "transport_hints": {
            "default": "local_loopback_json",
            "future": ["mutual_tls_json", "named_pipe_json_win32"],
        },
        "explicit_non_goals_now": [
            "No automated peer discovery.",
            "No cloud broker requirement.",
            "No replacement of MetaFramework.execute() for formal_analysis.",
        ],
    }


__all__ = [
    "A2A_PROTOCOL_ID",
    "A2A_PROTOCOL_VERSION",
    "build_a2a_capability_document",
]
