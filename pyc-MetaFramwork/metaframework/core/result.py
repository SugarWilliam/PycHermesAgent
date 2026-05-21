"""Structured execution result objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .evidence import EvidenceLevel


@dataclass
class ExecutionResult:
    capability_id: str
    success: bool
    validated: bool
    payload: Dict[str, Any] = field(default_factory=dict)
    evidence_level: EvidenceLevel = EvidenceLevel.C1
    method: str = ""
    engine: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["evidence_level"] = self.evidence_level.value
        return data
