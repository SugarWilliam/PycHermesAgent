"""Project rule discovery with AGENTS.md priority."""

from __future__ import annotations

from pathlib import Path
from typing import List


def discover_rule_files(start_path: Path) -> List[Path]:
    found = []
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    for path in [current, *current.parents]:
        agents = path / "AGENTS.md"
        claude = path / "CLAUDE.md"
        if agents.exists():
            found.append(agents)
            break
        if claude.exists():
            found.append(claude)
            break
    return found
