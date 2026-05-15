"""Runtime dataclasses for MetaFramework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .evidence import EvidenceLevel


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    display_name: str
    category: str
    engine_module: str
    engine_class: str
    default_evidence: EvidenceLevel
    max_evidence: EvidenceLevel
    required_dependencies: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    default_params: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    maturity: str = "stable"
    status: str = "active"
    legacy_aliases: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ExecutionRequest:
    capability_id: str
    data: Dict[str, Any]
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    requested_evidence: Optional[EvidenceLevel] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
