"""MRAG on-disk compatibility checks and documented migration path (no silent layout rewrites)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
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
            actions.append(f"blocked: {kb_id} index_format_version={iv_int} > supported {MRAG_INDEX_FORMAT_VERSION}; upgrade app")
        elif iv_int < MRAG_INDEX_FORMAT_VERSION:
            actions.append(f"note: {kb_id} on index_format_version={iv_int}; upgrade requires documented rebuild (see ADR / matrix)")
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
    parser.add_argument(
        "--backup-to",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Before planning, copy the entire storage_root tree into "
            "DIR/mrag_backup_<storage_leaf>_<UTC-timestamp>/ "
            "(copy runs only when storage_root exists; backup dir must not exist yet)."
        ),
    )
    args = parser.parse_args(argv)

    storage_root = args.storage_root.resolve()
    backup_path: Path | None = None
    if args.backup_to is not None:
        backup_parent = args.backup_to.resolve()
        if not storage_root.exists():
            print(f"backup skipped: storage root does not exist: {storage_root}", flush=True, file=sys.stderr)
        else:
            backup_parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = backup_parent / f"mrag_backup_{storage_root.name}_{stamp}"
            shutil.copytree(storage_root, backup_path, dirs_exist_ok=False)

    notes = plan_migrations(storage_root)
    blocked = any(line.startswith("blocked:") for line in notes)
    if args.json:
        payload = {"actions": notes, "blocked": blocked}
        if backup_path is not None:
            payload["backup_path"] = str(backup_path)
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        for line in notes:
            print(line)
    return 1 if blocked else 0


def cli_main() -> None:
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
