"""Contract tests for MRAG JSON→SQLite migration."""

import json
from pathlib import Path


from pyc_hermes_agent.mrag_core.migrate_to_sqlite import (
    migrate_all,
    migrate_knowledge_base,
    needs_migration,
)
from pyc_hermes_agent.mrag_core.sqlite_store import SQLiteChunkStore


def _make_chunks_json(kb_index_dir: Path, chunks: list[dict]) -> None:
    """Create a fake chunks.json in the given directory."""
    kb_index_dir.mkdir(parents=True, exist_ok=True)
    payload = {"index_format_version": 1, "chunks": chunks}
    (kb_index_dir / "chunks.json").write_text(json.dumps(payload), encoding="utf-8")


def _sample_chunks(n: int = 3) -> list[dict]:
    return [
        {
            "chunk_id": f"chunk-{i}",
            "document_id": "doc-1",
            "index": i,
            "text": f"Sample text for chunk {i}",
            "metadata": {"source_uri": "file:///test.txt", "start": i * 100, "end": (i + 1) * 100},
        }
        for i in range(n)
    ]


class TestNeedsMigration:
    def test_needs_migration_detects_json_chunks(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        _make_chunks_json(kb_dir, _sample_chunks())
        assert needs_migration(kb_dir) is True

    def test_needs_migration_false_when_db_exists(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        _make_chunks_json(kb_dir, _sample_chunks())
        (kb_dir / "chunks.db").write_bytes(b"")  # simulate existing DB
        assert needs_migration(kb_dir) is False

    def test_needs_migration_false_no_json(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        kb_dir.mkdir(parents=True)
        assert needs_migration(kb_dir) is False


class TestMigrateKnowledgeBase:
    def test_migrate_knowledge_base_creates_db(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        _make_chunks_json(kb_dir, _sample_chunks(5))

        result = migrate_knowledge_base(kb_dir, backup=False)

        assert result["status"] == "migrated"
        assert result["chunks_migrated"] == 5
        assert (kb_dir / "chunks.db").exists()

        # Verify DB contents
        with SQLiteChunkStore(kb_dir / "chunks.db") as store:
            assert store.count() == 5

    def test_migrate_creates_backup(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        _make_chunks_json(kb_dir, _sample_chunks(2))

        result = migrate_knowledge_base(kb_dir, backup=True)

        assert result["status"] == "migrated"
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_migrate_skips_already_migrated(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        _make_chunks_json(kb_dir, _sample_chunks())
        # Create existing DB
        with SQLiteChunkStore(kb_dir / "chunks.db"):
            pass  # just create empty DB

        result = migrate_knowledge_base(kb_dir, backup=True)
        assert result["status"] == "skipped"


class TestMigrateAll:
    def test_migrate_all_processes_multiple_kbs(self, tmp_path: Path) -> None:
        for kb_id in ("kb-alpha", "kb-beta"):
            _make_chunks_json(tmp_path / "indexes" / kb_id, _sample_chunks(2))

        results = migrate_all(tmp_path, backup=False)

        assert len(results) == 2
        assert all(r["status"] == "migrated" for r in results)
        assert all(r["chunks_migrated"] == 2 for r in results)

    def test_migrate_all_skips_already_migrated(self, tmp_path: Path) -> None:
        kb_dir = tmp_path / "indexes" / "kb1"
        _make_chunks_json(kb_dir, _sample_chunks())
        with SQLiteChunkStore(kb_dir / "chunks.db"):
            pass

        results = migrate_all(tmp_path, backup=False)

        assert len(results) == 1
        assert results[0]["status"] == "skipped"
