"""Migrate MRAG knowledge bases from JSON to SQLite/FTS5 storage."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pyc_hermes_agent.mrag_core.sqlite_store import ChunkRecord, SQLiteChunkStore


def needs_migration(kb_path: Path) -> bool:
    """Check if a knowledge base still uses JSON storage.

    Returns True if an indexes chunks.json exists AND no chunks.db exists.
    """
    chunks_json = kb_path / "chunks.json"
    chunks_db = kb_path / "chunks.db"
    return chunks_json.exists() and not chunks_db.exists()


def migrate_knowledge_base(kb_path: Path, *, backup: bool = True) -> dict:
    """Migrate a single knowledge base from JSON chunks to SQLite.

    Args:
        kb_path: Path to the knowledge base index directory (contains chunks.json).
        backup: If True, copy chunks.json to a timestamped backup before migration.

    Returns:
        {"kb_name": str, "status": "migrated"|"skipped"|"error",
         "chunks_migrated": int, "backup_path": str|None, "error": str|None}
    """
    kb_name = kb_path.name
    result: dict = {"kb_name": kb_name, "status": "skipped", "chunks_migrated": 0, "backup_path": None, "error": None}

    if not needs_migration(kb_path):
        return result

    chunks_json_path = kb_path / "chunks.json"
    backup_path: Optional[Path] = None

    try:
        # Backup
        if backup:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = kb_path / f"chunks_backup_{stamp}.json"
            shutil.copy2(chunks_json_path, backup_path)
            result["backup_path"] = str(backup_path)

        # Read JSON chunks
        raw = json.loads(chunks_json_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            chunk_list = raw.get("chunks", [])
        elif isinstance(raw, list):
            chunk_list = raw
        else:
            chunk_list = []

        # Convert to ChunkRecords
        records: list[ChunkRecord] = []
        for chunk in chunk_list:
            if not isinstance(chunk, dict):
                continue
            metadata = chunk.get("metadata", {})
            source_uri = ""
            if isinstance(metadata, dict):
                source_uri = metadata.get("source_uri", "")
            records.append(
                ChunkRecord(
                    chunk_id=chunk.get("chunk_id", ""),
                    document_id=chunk.get("document_id", ""),
                    content=chunk.get("text", ""),
                    source_uri=source_uri,
                    position=chunk.get("index", 0),
                    metadata=json.dumps(metadata) if isinstance(metadata, dict) else "{}",
                )
            )

        # Write to SQLite
        db_path = kb_path / "chunks.db"
        with SQLiteChunkStore(db_path) as store:
            if records:
                store.insert_chunks(records)

        result["status"] = "migrated"
        result["chunks_migrated"] = len(records)

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


def migrate_all(root: Path, *, backup: bool = True) -> list[dict]:
    """Migrate all knowledge bases under the MRAG storage root.

    Expects layout: root/indexes/<kb_id>/chunks.json
    """
    results: list[dict] = []
    indexes_root = root / "indexes"
    if not indexes_root.exists():
        return results

    for kb_dir in sorted(indexes_root.iterdir()):
        if kb_dir.is_dir():
            results.append(migrate_knowledge_base(kb_dir, backup=backup))

    return results
