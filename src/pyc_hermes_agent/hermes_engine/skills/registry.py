"""Skill registry — in-memory skill management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SkillDefinition:
    """A single skill that can be activated to inject context."""

    id: str
    name: str
    category: str  # "prompt" | "analysis" | "utility"
    description: str
    system_prompt_fragment: str  # injected when active
    active: bool = False


class SkillRegistry:
    """In-memory registry of available skills."""

    def __init__(self) -> None:
        self._skills: Dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """Register a skill definition."""
        self._skills[skill.id] = skill

    def activate(self, skill_id: str) -> bool:
        """Activate a skill by ID. Returns True if found."""
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        skill.active = True
        return True

    def deactivate(self, skill_id: str) -> bool:
        """Deactivate a skill by ID. Returns True if found."""
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        skill.active = False
        return True

    def get_active_prompt_fragments(self) -> List[str]:
        """Return system_prompt_fragment for all active skills."""
        return [s.system_prompt_fragment for s in self._skills.values() if s.active]

    def list_all(self) -> List[SkillDefinition]:
        """Return all registered skills."""
        return list(self._skills.values())

    def list_active(self) -> List[SkillDefinition]:
        """Return only active skills."""
        return [s for s in self._skills.values() if s.active]
