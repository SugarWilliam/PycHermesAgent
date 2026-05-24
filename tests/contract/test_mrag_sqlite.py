"""Contract tests for MRAG SQLite/FTS5 storage backend."""

import time
from pathlib import Path

import pytest

from pyc_hermes_agent.mrag_core.sqlite_store import ChunkRecord, SQLiteChunkStore


def _make_chunk(i: int, doc_id: str = "doc-1", content: str = "") -> ChunkRecord:
    return ChunkRecord(
        chunk_id=f"chunk-{i}",
        document_id=doc_id,
        content=content or f"Content for chunk number {i}",
        source_uri=f"file:///test/doc_{doc_id}.txt",
        position=i,
        metadata="{}",
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_kb" / "chunks.db"


def test_sqlite_store_create_and_insert(db_path: Path) -> None:
    with SQLiteChunkStore(db_path) as store:
        chunks = [_make_chunk(i) for i in range(10)]
        inserted = store.insert_chunks(chunks)
        assert inserted == 10
        assert store.count() == 10


def test_sqlite_store_fts5_search(db_path: Path) -> None:
    with SQLiteChunkStore(db_path) as store:
        store.insert_chunks(
            [
                ChunkRecord("c1", "d1", "Python is a programming language", "", 0, "{}"),
                ChunkRecord("c2", "d1", "SQLite provides full-text search", "", 1, "{}"),
                ChunkRecord("c3", "d1", "Java is another programming language", "", 2, "{}"),
            ]
        )
        results = store.search("programming language")
        assert len(results) >= 1
        ids = [r.chunk_id for r in results]
        assert "c1" in ids or "c3" in ids


def test_sqlite_store_delete_document(db_path: Path) -> None:
    with SQLiteChunkStore(db_path) as store:
        store.insert_chunks(
            [
                ChunkRecord("c1", "doc-a", "alpha content", "", 0, "{}"),
                ChunkRecord("c2", "doc-a", "beta content", "", 1, "{}"),
                ChunkRecord("c3", "doc-b", "gamma content", "", 0, "{}"),
            ]
        )
        deleted = store.delete_document("doc-a")
        assert deleted == 2
        assert store.count() == 1
        # FTS should not find deleted content
        results = store.search("alpha")
        assert len(results) == 0


def test_sqlite_store_empty_query(db_path: Path) -> None:
    with SQLiteChunkStore(db_path) as store:
        store.insert_chunks([_make_chunk(0)])
        assert store.search("") == []
        assert store.search("   ") == []


def test_sqlite_store_schema_version(db_path: Path) -> None:
    with SQLiteChunkStore(db_path) as store:
        cur = store._conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == str(SQLiteChunkStore.SCHEMA_VERSION)


def test_sqlite_store_context_manager(db_path: Path) -> None:
    store = SQLiteChunkStore(db_path)
    with store:
        assert store._conn is not None
        store.insert_chunks([_make_chunk(0)])
    assert store._conn is None


def test_sqlite_store_search_performance(db_path: Path) -> None:
    with SQLiteChunkStore(db_path) as store:
        chunks = [
            ChunkRecord(
                chunk_id=f"perf-{i}",
                document_id=f"doc-{i // 100}",
                content=f"Performance test chunk {i} with varied words like alpha beta gamma delta",
                source_uri="file:///perf.txt",
                position=i,
                metadata="{}",
            )
            for i in range(1000)
        ]
        store.insert_chunks(chunks)
        start = time.perf_counter()
        results = store.search("alpha beta")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert len(results) > 0
        assert elapsed_ms < 100, f"Search took {elapsed_ms:.1f}ms, expected <100ms"
