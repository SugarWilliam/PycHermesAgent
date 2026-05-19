"""Three-layer memory management for AgentLoop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class UserPreferences:
    """Persistent user preferences that influence agent behavior."""

    language: str = "en"
    analysis_conservatism: str = "moderate"  # conservative / moderate / aggressive
    preferred_output_style: str = "structured"  # brief / structured / detailed
    domain_hints: List[str] = field(default_factory=list)
    custom_instructions: str = ""

    def to_system_prompt_fragment(self) -> str:
        """Generate a system prompt fragment from preferences."""
        lines = [
            f"Language: {self.language} | Style: {self.preferred_output_style} | Conservatism: {self.analysis_conservatism}",
        ]
        if self.domain_hints:
            lines.append(f"Domains: {', '.join(self.domain_hints)}")
        if self.custom_instructions:
            lines.append(f"Custom: {self.custom_instructions}")
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        """Persist preferences to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "UserPreferences":
        """Load preferences from JSON, or return defaults."""
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()
            return cls(
                language=data.get("language", "en"),
                analysis_conservatism=data.get("analysis_conservatism", "moderate"),
                preferred_output_style=data.get("preferred_output_style", "structured"),
                domain_hints=data.get("domain_hints", []),
                custom_instructions=data.get("custom_instructions", ""),
            )
        except (json.JSONDecodeError, OSError):
            return cls()

    def merge(self, partial: Dict[str, Any]) -> None:
        """Apply a partial update to preferences."""
        for key, value in partial.items():
            if hasattr(self, key):
                setattr(self, key, value)


@dataclass
class MemoryLayers:
    """Container for the three memory layers."""

    session_messages: List[Dict[str, Any]] = field(default_factory=list)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    knowledge_base_ids: List[str] = field(default_factory=list)

    def build_context_injection(self) -> str:
        """Build the combined context string to inject into AgentLoop."""
        sections: List[str] = []

        # User Preferences section
        pref_fragment = self.preferences.to_system_prompt_fragment()
        sections.append(f"[User Preferences]\n{pref_fragment}")

        # Active Knowledge Bases section
        if self.knowledge_base_ids:
            kb_lines = "\n".join(f"- {kb_id}" for kb_id in self.knowledge_base_ids)
            sections.append(f"[Active Knowledge Bases]\n{kb_lines}")

        return "\n\n".join(sections)


def preferences_path(root: Path) -> Path:
    """Resolve the preferences file path under the given root."""
    return root / "config" / "preferences.json"


__all__ = ["MemoryLayers", "UserPreferences", "preferences_path"]
