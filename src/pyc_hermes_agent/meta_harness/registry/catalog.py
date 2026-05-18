"""Capability catalog for initial MetaHarness routing."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, TYPE_CHECKING

from pyc_hermes_agent.contracts import CapabilityDescriptor

if TYPE_CHECKING:
    from pyc_hermes_agent.meta_harness.bridge import LegacyMetaBridge


_DEFAULT_CAPABILITIES = [
    CapabilityDescriptor(
        id="A-12-FORECAST",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["forecast_adapters"],
        max_evidence_grade="CE-C1",
    ),
    CapabilityDescriptor(
        id="A-12-SCM",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["structural_causal"],
        max_evidence_grade="CE-C3",
    ),
    CapabilityDescriptor(
        id="A-13",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["org_personal_adapters"],
        max_evidence_grade="CE-C2",
    ),
    CapabilityDescriptor(
        id="A-14",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["org_personal_adapters"],
        max_evidence_grade="CE-C2",
    ),
    CapabilityDescriptor(
        id="A-15",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["org_personal_adapters"],
        max_evidence_grade="CE-C2",
    ),
    CapabilityDescriptor(
        id="A-18",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["complex_systems_adapters"],
        max_evidence_grade="CE-C2",
    ),
    CapabilityDescriptor(
        id="A-22",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["network_science_adapters"],
        max_evidence_grade="CE-C2",
    ),
    CapabilityDescriptor(
        id="A-23",
        kind="adapter",
        input_schema="meta.analysis.request.v1",
        output_schema="meta.analysis.result.v1",
        dependencies=["abm_adapter_v450"],
        max_evidence_grade="CE-C3",
    ),
]


class CapabilityRegistry:
    def __init__(self, bridge: Optional["LegacyMetaBridge"] = None) -> None:
        self._capabilities: Dict[str, CapabilityDescriptor] = {
            capability.id: capability for capability in _DEFAULT_CAPABILITIES
        }
        self._bridge = bridge

    def register(self, descriptor: CapabilityDescriptor) -> None:
        self._capabilities[descriptor.id] = descriptor

    def get(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        return self._capabilities.get(capability_id)

    def all(self) -> Iterable[CapabilityDescriptor]:
        return self._capabilities.values()

    def is_dependency_available(self, capability_id: str) -> bool:
        descriptor = self.get(capability_id)
        if descriptor is None:
            return False
        if self._bridge is None:
            return True
        return all(self._bridge.status(dep).available for dep in descriptor.dependencies)
