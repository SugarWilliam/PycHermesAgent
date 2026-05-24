"""A2A / sub-agent reserved capability surface."""

from __future__ import annotations

from typing import Any

from pyc_hermes_agent.contracts.a2a import build_a2a_capability_document

from .common import SIDECAR_API_VERSION


def get_a2a_capability_surface() -> dict[str, Any]:
    return build_a2a_capability_document(sidecar_api_version=SIDECAR_API_VERSION)


__all__ = ["get_a2a_capability_surface"]
