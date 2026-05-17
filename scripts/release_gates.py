#!/usr/bin/env python3
"""Engineering-preview release gates: tests, git whitespace, and secret heuristics.

Usage (from repo root):

    ./.venv/bin/python scripts/release_gates.py
    ./.venv/bin/python scripts/release_gates.py --no-pytest   # only whitespace + secret scan
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SKIP_PATH_PREFIXES = (
    "upstream/",
    "desktop/node_modules/",
    ".git/",
)

_TEXT_SUFFIXES = frozenset(
    {
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".yml",
        ".yaml",
        ".json",
        ".mjs",
        ".cjs",
        ".js",
        ".ts",
        ".tsx",
        ".sh",
    },
)

_EXTRA_SCAN_NAMES = frozenset({"Dockerfile", "Makefile", "Jenkinsfile"})

_MAX_SCAN_BYTES = 1_500_000

_SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ghp_[a-zA-Z0-9]{36}\b"), "GitHub classic PAT"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{82,}\b"), "GitHub fine-grained PAT"),
    (re.compile(r"\bsk-[a-zA-Z0-9]{32,}\b"), "OpenAI-style API key"),
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"), "PEM private key"),
]


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def _should_scan_path(rel: str) -> bool:
    if any(rel.startswith(p) for p in _SKIP_PATH_PREFIXES):
        return False
    path = Path(rel)
    if path.name in _EXTRA_SCAN_NAMES:
        return True
    return path.suffix.lower() in _TEXT_SUFFIXES


def _scan_tracked_files_for_secrets() -> list[str]:
    violations: list[str] = []
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return violations

    for rel in out.splitlines():
        if not rel or not _should_scan_path(rel):
            continue
        abs_path = ROOT / rel
        if not abs_path.is_file():
            continue
        try:
            size = abs_path.stat().st_size
        except OSError:
            continue
        if size > _MAX_SCAN_BYTES:
            continue
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for pattern, label in _SENSITIVE_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{rel}:{i}: possible {label}")

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PycHermesAgent engineering preview release gates")
    parser.add_argument(
        "--no-pytest",
        action="store_true",
        help="Skip pytest (run whitespace + secret checks only)",
    )
    args = parser.parse_args(argv)

    if not args.no_pytest:
        if _run([sys.executable, "-m", "pytest", "tests/contract", "-q"]) != 0:
            return 1

    if not (ROOT / ".git").is_dir():
        print("release_gates: no .git directory; skipping git and secret checks", flush=True)
        print("release_gates: OK", flush=True)
        return 0

    if _run(["git", "diff", "--check"]) != 0:
        return 1
    if _run(["git", "diff", "--cached", "--check"]) != 0:
        return 1

    secret_hits = _scan_tracked_files_for_secrets()
    if secret_hits:
        print("release_gates: possible secrets in tracked files (heuristic scan):", flush=True)
        for hit in secret_hits:
            print(" ", hit, flush=True)
        return 1

    print("release_gates: OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
