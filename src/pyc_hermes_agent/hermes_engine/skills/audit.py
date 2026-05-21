"""Skill activation/usage audit trail."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SkillAuditEntry:
    skill_id: str
    action: str  # "activated" | "deactivated" | "used"
    timestamp: str  # ISO format
    session_id: str = ""


class SkillAuditor:
    """Track skill activation/deactivation events and usage counts."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._entries: list[SkillAuditEntry] = []
        self._usage_counts: dict[str, int] = {}
        self._storage_path = storage_path

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_activation(self, skill_id: str, session_id: str = "") -> None:
        self._entries.append(
            SkillAuditEntry(skill_id=skill_id, action="activated", timestamp=self._now(), session_id=session_id)
        )

    def record_deactivation(self, skill_id: str, session_id: str = "") -> None:
        self._entries.append(
            SkillAuditEntry(skill_id=skill_id, action="deactivated", timestamp=self._now(), session_id=session_id)
        )

    def record_usage(self, skill_id: str, session_id: str = "") -> None:
        self._entries.append(
            SkillAuditEntry(skill_id=skill_id, action="used", timestamp=self._now(), session_id=session_id)
        )
        self._usage_counts[skill_id] = self._usage_counts.get(skill_id, 0) + 1

    def get_usage_counts(self) -> dict[str, int]:
        return dict(self._usage_counts)

    def get_recent_entries(self, limit: int = 50) -> list[SkillAuditEntry]:
        return self._entries[-limit:]

    def save(self) -> None:
        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "entries": [asdict(e) for e in self._entries],
            "usage_counts": self._usage_counts,
        }
        self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        self._entries = [SkillAuditEntry(**e) for e in raw.get("entries", [])]
        self._usage_counts = raw.get("usage_counts", {})
