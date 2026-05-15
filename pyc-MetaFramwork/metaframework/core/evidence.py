"""Evidence level definitions and helpers."""

from __future__ import annotations

from enum import Enum


class EvidenceLevel(str, Enum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C3_PLUS = "C3+"
    C4 = "C4"


_EVIDENCE_ORDER = {
    EvidenceLevel.C1: 1,
    EvidenceLevel.C2: 2,
    EvidenceLevel.C3: 3,
    EvidenceLevel.C3_PLUS: 4,
    EvidenceLevel.C4: 5,
}


def clamp_evidence_level(requested: EvidenceLevel | None, maximum: EvidenceLevel) -> EvidenceLevel:
    if requested is None:
        return maximum
    return requested if _EVIDENCE_ORDER[requested] <= _EVIDENCE_ORDER[maximum] else maximum
