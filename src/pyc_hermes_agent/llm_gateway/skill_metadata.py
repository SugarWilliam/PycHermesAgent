"""Skill metadata parsing for `.opencode/skills/*/SKILL.md`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass(slots=True)
class SkillMetadata:
    name: str
    description: str
    path: Path
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


def parse_skill_metadata(path: Path) -> SkillMetadata:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError(f"Skill frontmatter missing in {path}")

    frontmatter: Dict[str, str] = {}
    nested_metadata: Dict[str, str] = {}
    in_metadata_block = False

    idx = 1
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---":
            break

        if in_metadata_block and line.startswith("  "):
            if ":" in line:
                key, value = line.strip().split(":", 1)
                nested_metadata[key.strip()] = value.strip()
            idx += 1
            continue

        in_metadata_block = False
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "metadata":
                in_metadata_block = True
            else:
                frontmatter[key] = value
        idx += 1

    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not name or not description:
        raise ValueError(f"Skill metadata missing required fields in {path}")

    return SkillMetadata(
        name=name,
        description=description,
        path=path,
        license=frontmatter.get("license"),
        compatibility=frontmatter.get("compatibility"),
        metadata=nested_metadata,
    )
