"""Track D — skill activation ordering, overlap-group hints, lightweight audit payloads."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pyc_hermes_agent.llm_gateway.skills import load_skill_metadata


def sort_skill_names_for_context(workspace_root: Path, skill_names: Sequence[str]) -> list[str]:
    """Reorder explicit activations so higher numeric ``priority`` front-matter resolves first."""

    workspace_root = workspace_root.expanduser().resolve()

    ordered_unique: list[str] = []

    positions: dict[str, int] = {}

    seen: set[str] = set()

    for idx, raw in enumerate(skill_names or []):
        key = raw.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered_unique.append(key)
        positions[key] = idx

    if not ordered_unique:
        return []

    by_name = {m.name: m for m in load_skill_metadata(workspace_root)}

    def sort_key(name: str) -> tuple[int, int, str]:
        meta = by_name.get(name)
        prio = meta.priority if meta else 0
        pos = positions.get(name, 0)
        return (-prio, pos, name.lower())

    return sorted(ordered_unique, key=sort_key)


def collect_skill_audit_hints(workspace_root: Path, skill_names: Sequence[str]) -> dict[str, Any]:
    normalized = sort_skill_names_for_context(workspace_root, skill_names)

    metas_by_name = {m.name: m for m in load_skill_metadata(workspace_root.expanduser())}

    active_rows: list[dict[str, Any]] = []
    for nm in normalized:
        md = metas_by_name.get(nm)
        og = ""
        origin = ""

        prio = 0

        if md is not None:
            prio = md.priority
            origin = md.skill_origin
            og = md.overlap_group.strip() if md.overlap_group else ""

        active_rows.append(
            {
                "name": nm,
                "priority": prio,
                "overlap_group": og or None,
                "origin": origin,
            }
        )

    groups: dict[str, list[str]] = {}
    for row in active_rows:
        grp = row.get("overlap_group")
        nm = row.get("name")

        if not isinstance(grp, str) or not grp or not isinstance(nm, str):
            continue

        groups.setdefault(grp, []).append(nm)

    conflicts: list[dict[str, Any]] = []
    for grp, members in groups.items():
        if len(members) >= 2:
            conflicts.append(
                {
                    "kind": "overlap_group_multi_activate",
                    "overlap_group": grp,
                    "skills": sorted(members),
                    "hint": (
                        "Multiple skills from the same overlap_group are activated; "
                        "review for redundant or conflicting directives."
                    ),
                }
            )

    return {"activation_order": active_rows, "overlap_group_hints": conflicts}


__all__ = ["collect_skill_audit_hints", "sort_skill_names_for_context"]
