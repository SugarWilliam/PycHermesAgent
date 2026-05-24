#!/usr/bin/env python3
"""Phase 3F — IPC-style business MRAG benchmark (deterministic, offline)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if __package__ is None:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.mrag.ipc_semantic_benchmark import run_ipc_business_benchmark


def main() -> int:
    failures, lines = run_ipc_business_benchmark()
    for ln in lines:
        print(ln)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
