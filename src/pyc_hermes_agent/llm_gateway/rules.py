"""Project rule discovery with AGENTS.md priority."""

from __future__ import annotations

from pathlib import Path
from typing import List


def discover_rule_files(start_path: Path) -> List[Path]:
    """Backward-compatible shallow discovery (nearest hit walking upward)."""

    docs = discover_ordered_rule_documents(start_path)
    return [docs[-1]] if docs else []


def discover_ordered_rule_documents(start_path: Path) -> List[Path]:
    """
    Ordered rule documents from filesystem root outward → workspace (``start_path``).

    For each ancestor directory prefer ``AGENTS.md`` over ``CLAUDE.md``.
    """
    seen: set[Path] = set()
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    ancestors: List[Path] = []

    p = current
    while True:
        ancestors.append(p)
        parent = p.parent
        if parent == p:
            break

        p = parent

    ancestors.reverse()

    collected: List[Path] = []

    for ancestor in ancestors:
        agents = ancestor / "AGENTS.md"

        claude = ancestor / "CLAUDE.md"

        picked: Path | None = None

        if agents.is_file():
            picked = agents

        elif claude.is_file():
            picked = claude
        if picked is None:
            continue

        rp = picked.resolve()
        if rp in seen:
            continue

        seen.add(rp)

        collected.append(rp)

    return collected
