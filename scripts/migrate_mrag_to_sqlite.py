"""CLI: migrate MRAG knowledge bases from JSON to SQLite."""

import sys
from pathlib import Path

from pyc_hermes_agent.mrag_core.migrate_to_sqlite import migrate_all


def main() -> int:
    backup = True
    args = [a for a in sys.argv[1:] if a != "--no-backup"]
    if len(args) != len(sys.argv[1:]):
        backup = False

    root = Path(args[0]) if args else Path(".")
    results = migrate_all(root, backup=backup)

    if not results:
        print("No knowledge bases found to migrate.")
        return 0

    for r in results:
        print(f"  {r['kb_name']}: {r['status']} ({r.get('chunks_migrated', 0)} chunks)")

    return 0 if all(r["status"] != "error" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
