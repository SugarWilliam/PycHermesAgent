"""Core types and protocols for MetaFramework."""

from .evidence import EvidenceLevel, clamp_evidence_level
from .result import ExecutionResult
from .types import CapabilitySpec, ExecutionRequest

__all__ = [
    "CapabilitySpec",
    "ExecutionRequest",
    "ExecutionResult",
    "EvidenceLevel",
    "clamp_evidence_level",
]
