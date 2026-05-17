#!/usr/bin/env python3
"""Engineering-preview release gates: contract tests plus git whitespace checks.

Usage (from repo root):

    ./.venv/bin/python scripts/release_gates.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    if _run([sys.executable, "-m", "pytest", "tests/contract", "-q"]) != 0:
        return 1

    if not (ROOT / ".git").is_dir():
        print("release_gates: no .git directory; skipping git checks", flush=True)
        return 0

    if _run(["git", "diff", "--check"]) != 0:
        return 1
    if _run(["git", "diff", "--cached", "--check"]) != 0:
        return 1

    print("release_gates: OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
