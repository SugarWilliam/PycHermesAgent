"""MRAG on-disk compatibility checks and documented migration path (no silent layout rewrites)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyc_hermes_agent.mrag_core.persistence import MRAG_INDEX_FORMAT_VERSION


def plan_migrations(storage_root: Path) -> list[str]:
    """Return human-readable migration notes. Phase 2+ may add automatic upgrades; today this validates layout."""
    actions: list[str] = []
    kb_root = storage_root / "knowledge_bases"
    if not kb_root.exists():
        actions.append("ok: no knowledge_bases directory (empty store)")
        return actions

    for manifest_path in sorted(kb_root.glob("*/manifest.json")):
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            actions.append(f"skip: invalid manifest {manifest_path}")
            continue
        iv = raw.get("index_format_version")
        try:
            iv_int = int(iv) if iv is not None else 1
        except (TypeError, ValueError):
            actions.append(f"invalid index_format_version in {manifest_path}")
            continue
        kb_id = raw.get("knowledge_base_id", manifest_path.parent.name)
        if iv_int > MRAG_INDEX_FORMAT_VERSION:
            actions.append(
                f"blocked: {kb_id} index_format_version={iv_int} > supported {MRAG_INDEX_FORMAT_VERSION}; upgrade app"
            )
        elif iv_int < MRAG_INDEX_FORMAT_VERSION:
            actions.append(
                f"note: {kb_id} on index_format_version={iv_int}; upgrade requires documented rebuild (see ADR / matrix)"
            )
        else:
            actions.append(f"ok: {kb_id} index_format_version={iv_int}")

    return actions or ["ok: no manifests found"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MRAG storage migration / compatibility planner.")
    parser.add_argument(
        "storage_root",
        type=Path,
        help="MRAG storage root (same tree as MRAGService storage_root).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON object instead of line-oriented text.",
    )
    args = parser.parse_args(argv)
    notes = plan_migrations(args.storage_root.resolve())
    blocked = any(line.startswith("blocked:") for line in notes)
    if args.json:
        print(json.dumps({"actions": notes, "blocked": blocked}, ensure_ascii=True, indent=2))
    else:
        for line in notes:
            print(line)
    return 1 if blocked else 0


def cli_main() -> None:
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
