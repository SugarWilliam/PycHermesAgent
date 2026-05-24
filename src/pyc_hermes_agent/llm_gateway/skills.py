"""Project-local skill discovery compatible with `.opencode/skills`."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import List

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.llm_gateway.skill_metadata import SkillMetadata, parse_skill_metadata

_USER_SKILLS_ENV = "PYC_HERMES_USER_SKILLS_HOME"


def discover_runtime_managed_user_skills(local_data_dir: Path) -> List[Path]:
    """Skills published under writable ``user_skills/*/SKILL.md`` (sidecar-managed, Phase 3D)."""

    root = local_data_dir / "user_skills"
    if not root.is_dir():
        return []
    return sorted(root.glob("*/SKILL.md"))


def discover_skills(start_path: Path) -> List[Path]:
    """Return project-discovered ``SKILL.md`` paths (walks ``start_path`` parents for ``.opencode/skills``)."""
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
    """Merge skills: env-user → runtime user_skills → project (project wins name collisions).

    Env path uses ``PYC_HERMES_USER_SKILLS_HOME``. Runtime-managed skills live under
    ``ensure_runtime_directories(resolve_runtime_paths(workspace)).local_data_dir / "user_skills"``.
    """

    merged: dict[str, SkillMetadata] = {}

    user_root_raw = os.environ.get(_USER_SKILLS_ENV, "").strip()

    if user_root_raw:
        uh = Path(user_root_raw).expanduser()
        if uh.is_dir():
            for skill_path in sorted(uh.glob("*/SKILL.md")):
                meta = replace(parse_skill_metadata(skill_path), skill_origin="user")
                merged[meta.name] = meta

    paths = ensure_runtime_directories(resolve_runtime_paths(start_path))
    for skill_path in discover_runtime_managed_user_skills(paths.local_data_dir):
        meta = replace(parse_skill_metadata(skill_path), skill_origin="user_local")
        merged[meta.name] = meta

    for skill_path in discover_skills(start_path):
        meta = replace(parse_skill_metadata(skill_path), skill_origin="project")
        merged[meta.name] = meta

    return [merged[name] for name in sorted(merged.keys())]
