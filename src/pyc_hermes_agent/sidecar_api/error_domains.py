"""Stable `ErrorEnvelope.domain` values for sidecar and HTTP surfaces.

Keep codes specific; domains group errors for clients, telemetry, and release notes.
"""

from __future__ import annotations

DOMAIN_INTERNAL = "internal"
DOMAIN_HTTP = "http"
DOMAIN_META_HARNESS = "meta_harness"
DOMAIN_LLM = "llm"
DOMAIN_MRAG = "mrag"
DOMAIN_AGENT = "agent"
DOMAIN_ASSET = "asset"
DOMAIN_ARTIFACT = "artifact"
DOMAIN_HERMES = "hermes"

__all__ = [
    "DOMAIN_AGENT",
    "DOMAIN_ARTIFACT",
    "DOMAIN_ASSET",
    "DOMAIN_HERMES",
    "DOMAIN_HTTP",
    "DOMAIN_INTERNAL",
    "DOMAIN_LLM",
    "DOMAIN_META_HARNESS",
    "DOMAIN_MRAG",
]
