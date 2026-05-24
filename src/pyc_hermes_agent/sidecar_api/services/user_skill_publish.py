"""Write user-managed SKILL.md under runtime local-data (never install dir)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.llm_gateway.skill_metadata import parse_skill_metadata
from pyc_hermes_agent.sidecar_api.services.common import _repo_root, resolve_runtime_directories_root

_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62})$", re.I)


def _sanitize_skill_slug(raw: str) -> str:

    slug = "".join(ch.lower() if ch.isalnum() or ch in "-_." else "-" for ch in raw.strip())
    slug = slug.strip("-._")
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-._")
    if slug and (slug[0] in ".-_" or slug.endswith((".", "_", "-"))):
        slug = slug.strip("-._")

    if not _SLUG.match(slug or ""):

        raise ValueError(f"skill_id '{raw}' resolves to unsafe slug.")

    return slug


def persist_user_skill_markdown(

    *,
    skill_id_raw: str,

    markdown_body: str,

    root: Path | None = None,

) -> dict[str, Any]:
    workspace = resolve_runtime_directories_root(root) or _repo_root()

    paths = ensure_runtime_directories(resolve_runtime_paths(workspace))

    skill_dir_root = paths.local_data_dir / "user_skills"

    skill_dir_root.mkdir(parents=True, exist_ok=True)

    slug = _sanitize_skill_slug(skill_id_raw)

    bundle_dir = skill_dir_root / slug

    bundle_dir.mkdir(parents=True, exist_ok=True)

    target = bundle_dir / "SKILL.md"

    markdown = markdown_body.strip() + ("\n" if markdown_body.strip() else "")

    target.write_text(markdown if markdown else markdown_body, encoding="utf-8")

    meta = parse_skill_metadata(target)

    return {

        "skill_id": meta.name,

        "path": str(target),

        "slug": slug,

        "skill_origin": "user_local",

        "description": meta.description,

    }


__all__ = ["persist_user_skill_markdown", "_sanitize_skill_slug"]
