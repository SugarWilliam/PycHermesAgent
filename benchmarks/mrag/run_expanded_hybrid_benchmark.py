#!/usr/bin/env python3
"""Phase 3F — expanded lexical vs hybrid MRAG benchmark (offline / deterministic).

Run from repo root::

    uv run python benchmarks/mrag/run_expanded_hybrid_benchmark.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if __package__ is None:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.mrag.expanded_benchmark import run_expanded_benchmark


def main() -> int:
    exit_code, lines = run_expanded_benchmark()
    for ln in lines:
        print(ln)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
