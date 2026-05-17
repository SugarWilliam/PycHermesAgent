"""Emit resolved runtime paths and validate install immutability (preview helper)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.packaging.policy import validate_runtime_paths_outside_install


def _paths_dict(paths) -> dict[str, str]:
    d = asdict(paths)
    return {k: str(v) for k, v in d.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print resolved runtime paths for packaging review.")
    parser.add_argument(
        "--workspace-root",
        default="",
        help="Optional workspace/install root for read-only discovery (same as sidecar --root).",
    )
    parser.add_argument(
        "--mkdirs",
        action="store_true",
        help="Create directories after resolution (like a running sidecar).",
    )
    args = parser.parse_args(argv)

    root = Path(args.workspace_root).resolve() if args.workspace_root else None
    install = os.environ.get("PYC_HERMES_INSTALL_DIR", "").strip()
    enforced = os.environ.get("PYC_HERMES_ENFORCE_PACKAGING_RULES", "").strip().lower() in {"1", "true", "yes"}

    try:
        raw_paths = resolve_runtime_paths(root)
    except RuntimeError as exc:
        payload: dict[str, object] = {
            "packaging_rules_enforced": enforced,
            "workspace_root": str(root) if root else None,
            "install_dir": install or None,
            "install_immutability": "failed",
            "install_immutability_error": str(exc),
        }
        print(json.dumps(payload, indent=2))
        return 1

    paths = ensure_runtime_directories(raw_paths) if args.mkdirs else raw_paths

    payload = {
        "packaging_rules_enforced": enforced,
        "workspace_root": str(root) if root else None,
        "install_dir": install or None,
        "paths": _paths_dict(paths),
    }

    if install:
        try:
            validate_runtime_paths_outside_install(paths, Path(install))
            payload["install_immutability"] = "ok"
        except RuntimeError as exc:
            payload["install_immutability"] = "failed"
            payload["install_immutability_error"] = str(exc)
            print(json.dumps(payload, indent=2), file=sys.stdout)
            return 1

    print(json.dumps(payload, indent=2))
    return 0


def cli_main() -> None:
    """Setuptools console_script entry (no argv parameter)."""
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
