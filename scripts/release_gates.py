#!/usr/bin/env python3
"""Engineering and production-oriented release gates: tests, optional static checks, packaging probes.

Usage (from repo root):

    ./.venv/bin/python scripts/release_gates.py
    ./.venv/bin/python scripts/release_gates.py --no-pytest
        # whitespace + secret scan only; optional --with-ruff / --with-mypy / --with-production still apply
    ./.venv/bin/python scripts/release_gates.py --with-ruff              # env RELEASE_GATES_RUFF=1
    ./.venv/bin/python scripts/release_gates.py --with-mypy            # env RELEASE_GATES_MYPY=1
    ./.venv/bin/python scripts/release_gates.py --with-production      # env RELEASE_GATES_PRODUCTION=1

Production extras (after ruff/mypy when enabled): ``uv lock --check``, Python CycloneDX 1.5 SBOM export (``uv export``),
MRAG migrate CLI on a temp dir with ``--backup-to``, ``npm ci`` + ``npm audit --omit=dev --audit-level=critical``
+ ``npm run dist:linux`` under ``desktop/`` (requires npm). Optional ``RELEASE_GATES_PYINSTALLER=1`` verifies the ``ga``
extra (PyInstaller import). See ``docs/deployment/Production_Release_Gates.md``.

    ./.venv/bin/python scripts/release_gates.py --export-meta-benchmarks DIR
    ./.venv/bin/python scripts/release_gates.py --write-preview-release-notes FILE.md

Whitespace checks: locally, unstaged and staged diffs are scanned. In GitHub Actions (set
``GITHUB_EVENT_NAME`` / ``GITHUB_BASE_REF``), pull requests use ``origin/<base>...HEAD``.
Override with ``RELEASE_GATES_DIFF_RANGE`` (e.g. ``origin/main...HEAD``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=cwd)


def _git_whitespace_gates() -> int:
    """Reject conflict markers / bad whitespace in meaningful diffs (CI-aware)."""
    diff_range = os.environ.get("RELEASE_GATES_DIFF_RANGE", "").strip()
    if diff_range:
        return _run(["git", "diff", "--check", diff_range])

    event = os.environ.get("GITHUB_EVENT_NAME", "")
    if event == "pull_request":
        base = os.environ.get("GITHUB_BASE_REF", "").strip()
        if base:
            return _run(["git", "diff", "--check", f"origin/{base}...HEAD"])

    if event == "push":
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD~1"],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            return 0
        return _run(["git", "diff", "--check", "HEAD~1", "HEAD"])

    if _run(["git", "diff", "--check"]) != 0:
        return 1
    if _run(["git", "diff", "--cached", "--check"]) != 0:
        return 1
    return 0


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
    parser.add_argument(
        "--with-ruff",
        action="store_true",
        help="After pytest: run ruff check on src, tests, scripts (also RELEASE_GATES_RUFF=1)",
    )
    parser.add_argument(
        "--with-mypy",
        action="store_true",
        help="After pytest: run mypy on package (RELEASE_GATES_MYPY=1 in CI)",
    )
    parser.add_argument(
        "--export-meta-benchmarks",
        type=Path,
        default=None,
        metavar="DIR",
        help="After gates pass, write meta_harness_benchmarks.json under DIR and verify smoke/value_proof passed",
    )
    parser.add_argument(
        "--write-preview-release-notes",
        type=Path,
        default=None,
        metavar="FILE",
        help="After gates pass, write preview release-notes draft (see scripts/generate_preview_release_notes.py)",
    )
    parser.add_argument(
        "--with-production",
        action="store_true",
        help=(
            "After static checks: uv lock --check, CycloneDX SBOM export, MRAG migrate+backup smoke, "
            "npm audit (critical+) and desktop dist:linux (RELEASE_GATES_PRODUCTION=1)"
        ),
    )
    args = parser.parse_args(argv)

    if not args.no_pytest:
        if _run([sys.executable, "-m", "pytest", "tests", "-q"]) != 0:
            return 1

    want_ruff = args.with_ruff or os.environ.get("RELEASE_GATES_RUFF", "").lower() in ("1", "true", "yes")
    if want_ruff:
        if _run([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"]) != 0:
            return 1

    want_mypy = args.with_mypy or os.environ.get("RELEASE_GATES_MYPY", "").lower() in ("1", "true", "yes")
    if want_mypy:
        if _run([sys.executable, "-m", "mypy", "-p", "pyc_hermes_agent"]) != 0:
            return 1

    want_prod = (
        args.with_production
        or os.environ.get("RELEASE_GATES_PRODUCTION", "").lower() in ("1", "true", "yes")
    )
    if want_prod:
        uv_bin = shutil.which("uv")
        if not uv_bin:
            print("release_gates: production requires uv on PATH", flush=True)
            return 1
        if _run([uv_bin, "lock", "--check"], cwd=ROOT) != 0:
            return 1
        (ROOT / "build").mkdir(exist_ok=True)
        sbom_path = ROOT / "build" / "sbom-python.cdx.json"
        if (
            _run(
                [
                    uv_bin,
                    "export",
                    "-q",
                    "--frozen",
                    "--no-dev",
                    "--format",
                    "cyclonedx1.5",
                    "-o",
                    str(sbom_path),
                ],
                cwd=ROOT,
            )
            != 0
        ):
            return 1
        try:
            sbom_payload = json.loads(sbom_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"release_gates: CycloneDX export not readable JSON: {exc}", flush=True)
            return 1
        if sbom_payload.get("bomFormat") != "CycloneDX":
            print("release_gates: CycloneDX export missing bomFormat=CycloneDX", flush=True)
            return 1

        want_pyinstaller = os.environ.get("RELEASE_GATES_PYINSTALLER", "").lower() in ("1", "true", "yes")
        if want_pyinstaller:
            if _run([uv_bin, "sync", "--frozen", "--extra", "dev", "--extra", "ga"], cwd=ROOT) != 0:
                return 1
            if (
                subprocess.run([sys.executable, "-c", "import PyInstaller"], cwd=ROOT, check=False).returncode != 0
            ):
                print("release_gates: PyInstaller import failed (needs ga extra synced)", flush=True)
                return 1
            print("release_gates: PyInstaller (ga extra) import OK", flush=True)

        with tempfile.TemporaryDirectory() as migrate_base:
            mrag_storage = Path(migrate_base) / "mrag_store"
            mrag_storage.mkdir()
            backup_parent = Path(migrate_base) / "migrate_backups"
            mrag_cli = shutil.which("pyc-hermes-mrag-migrate")
            migrate_argv: list[str]
            if mrag_cli:
                migrate_argv = [
                    mrag_cli,
                    str(mrag_storage),
                    "--json",
                    "--backup-to",
                    str(backup_parent),
                ]
            else:
                migrate_argv = [
                    sys.executable,
                    "-m",
                    "pyc_hermes_agent.mrag_core.migrate",
                    str(mrag_storage),
                    "--json",
                    "--backup-to",
                    str(backup_parent),
                ]
            if _run(migrate_argv) != 0:
                return 1
            backups = sorted(backup_parent.glob("mrag_backup_*"))
            if not backups:
                print(
                    "release_gates: production: migrate --backup-to produced no mrag_backup_* dir",
                    flush=True,
                )
                return 1
        desktop = ROOT / "desktop"
        npm_bin = shutil.which("npm")
        if (desktop / "package.json").is_file():
            if not npm_bin:
                print("release_gates: production: npm not on PATH (desktop pack skipped — failing gate)", flush=True)
                return 1
            if not (desktop / "package-lock.json").is_file():
                print("release_gates: production: desktop/package-lock.json missing", flush=True)
                return 1
            if _run([npm_bin, "ci"], cwd=desktop) != 0:
                return 1
            if _run([npm_bin, "audit", "--omit=dev", "--audit-level=critical"], cwd=desktop) != 0:
                return 1
            if _run([npm_bin, "run", "dist:linux"], cwd=desktop) != 0:
                return 1
        print("release_gates: production packaging checks OK", flush=True)

    if not (ROOT / ".git").is_dir():
        print("release_gates: no .git directory; skipping git and secret checks", flush=True)
        print("release_gates: OK", flush=True)
        return 0

    if _git_whitespace_gates() != 0:
        return 1

    secret_hits = _scan_tracked_files_for_secrets()
    if secret_hits:
        print("release_gates: possible secrets in tracked files (heuristic scan):", flush=True)
        for hit in secret_hits:
            print(" ", hit, flush=True)
        return 1

    if args.export_meta_benchmarks is not None:
        out_dir = args.export_meta_benchmarks.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "meta_harness_benchmarks.json"
        export_script = ROOT / "scripts" / "export_meta_harness_benchmarks.py"
        if _run([sys.executable, str(export_script), "-o", str(out_path)]) != 0:
            return 1
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"release_gates: could not read benchmark export: {exc}", flush=True)
            return 1
        smoke = data.get("benchmark_smoke") or {}
        proof = data.get("value_proof") or {}
        if not smoke.get("passed"):
            print("release_gates: benchmark_smoke did not pass", flush=True)
            return 1
        if not proof.get("passed"):
            print("release_gates: value_proof benchmark did not pass", flush=True)
            return 1
        print(f"release_gates: wrote {out_path}", flush=True)

    if args.write_preview_release_notes is not None:
        out = args.write_preview_release_notes.resolve()
        gen_script = ROOT / "scripts" / "generate_preview_release_notes.py"
        if _run([sys.executable, str(gen_script), "-o", str(out)]) != 0:
            return 1
        print(f"release_gates: wrote preview release notes draft {out}", flush=True)

    print("release_gates: OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
