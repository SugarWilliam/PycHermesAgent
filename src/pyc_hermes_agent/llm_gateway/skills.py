"""Project-local skill discovery compatible with `.opencode/skills`."""

from __future__ import annotations

from pathlib import Path
from typing import List

from pyc_hermes_agent.llm_gateway.skill_metadata import SkillMetadata, parse_skill_metadata


def discover_skills(start_path: Path) -> List[Path]:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    matches: List[Path] = []
    for path in [current, *current.parents]:
        root = path / ".opencode" / "skills"
        if root.exists():
            matches.extend(sorted(root.glob("*/SKILL.md")))
    return matches


def load_skill_metadata(start_path: Path) -> List[SkillMetadata]:
    metadata: List[SkillMetadata] = []
    for skill_path in discover_skills(start_path):
        metadata.append(parse_skill_metadata(skill_path))
    return metadata
