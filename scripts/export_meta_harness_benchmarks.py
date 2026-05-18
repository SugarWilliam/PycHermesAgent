#!/usr/bin/env python3
"""Export MetaHarness smoke and value-proof benchmarks as JSON (for release notes / CI artifacts).

Usage (from repo root):

    ./.venv/bin/python scripts/export_meta_harness_benchmarks.py
    ./.venv/bin/python scripts/export_meta_harness_benchmarks.py -o build/meta_harness_benchmarks.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))

    parser = argparse.ArgumentParser(description="Export MetaHarness benchmark JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write JSON to this file instead of stdout",
    )
    args = parser.parse_args(argv)

    from pyc_hermes_agent.meta_harness import MetaFramework
    from pyc_hermes_agent.meta_harness.benchmark import run_value_proof_benchmark

    framework = MetaFramework()
    payload = {
        "meta": {"tool": "export_meta_harness_benchmarks", "entrypoint": "MetaFramework.execute"},
        "benchmark_smoke": framework.run_benchmark_smoke(),
        "value_proof": run_value_proof_benchmark(framework),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
