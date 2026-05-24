"""Concurrency tests for thread-safe components."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pyc_hermes_agent.hermes_engine.memory import UserPreferences
from pyc_hermes_agent.mrag_core.sqlite_store import ChunkRecord, SQLiteChunkStore
from pyc_hermes_agent.sidecar_api.services.mrag_service import MRAGServiceRegistry


def test_mrag_registry_concurrent_access(tmp_path: Path) -> None:
    """10 threads call get with same root — only 1 MRAGService instance created."""
    registry = MRAGServiceRegistry()
    results: list = []
    barrier = threading.Barrier(10)

    def _get():
        barrier.wait()
        return registry.get(tmp_path)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_get) for _ in range(10)]
        results = [f.result() for f in as_completed(futures)]

    # All must be the same instance
    assert len(set(id(r) for r in results)) == 1


def test_mrag_registry_concurrent_different_names(tmp_path: Path) -> None:
    """5 threads create services with different roots — 5 distinct instances."""
    registry = MRAGServiceRegistry()
    roots = [tmp_path / f"kb_{i}" for i in range(5)]
    for r in roots:
        r.mkdir()
    barrier = threading.Barrier(5)

    def _get(root):
        barrier.wait()
        return registry.get(root)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_get, r) for r in roots]
        results = [f.result() for f in as_completed(futures)]

    assert len(set(id(r) for r in results)) == 5


def test_sqlite_store_concurrent_inserts(tmp_path: Path) -> None:
    """5 threads insert chunks into same DB — total count correct.

    Uses per-thread connections (the production pattern) to avoid SQLite
    shared-connection threading issues on network filesystems.
    """

    db_path = tmp_path / "chunks.db"
    # Initialize schema with a primary store
    store = SQLiteChunkStore(db_path)
    store.open()
    store.close()

    chunks_per_thread = 20
    barrier = threading.Barrier(5)
    threading.Lock()

    def _insert(thread_idx: int):
        barrier.wait()
        local_store = SQLiteChunkStore(db_path)
        local_store.open()
        local_store._conn.execute("PRAGMA busy_timeout=10000")
        chunks = [
            ChunkRecord(
                chunk_id=f"t{thread_idx}-c{i}",
                document_id=f"doc-{thread_idx}",
                content=f"content from thread {thread_idx} chunk {i}",
                source_uri="test://source",
                position=i,
                metadata="{}",
            )
            for i in range(chunks_per_thread)
        ]
        local_store.insert_chunks(chunks)
        local_store.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_insert, idx) for idx in range(5)]
        for f in as_completed(futures):
            f.result()  # propagate exceptions

    verify = SQLiteChunkStore(db_path)
    verify.open()
    assert verify.count() == 5 * chunks_per_thread
    verify.close()


def test_sqlite_store_concurrent_search_during_insert(tmp_path: Path) -> None:
    """1 thread inserts, 3 threads search simultaneously — no crashes.

    Each thread uses its own SQLiteChunkStore/connection (production pattern).
    """
    import sqlite3

    db_path = tmp_path / "chunks.db"
    store = SQLiteChunkStore(db_path)
    store.open()
    store._conn.execute("PRAGMA busy_timeout=10000")

    # Seed some data so searches have something to find
    seed = [
        ChunkRecord(
            chunk_id=f"seed-{i}",
            document_id="doc-seed",
            content=f"searchable content number {i}",
            source_uri="test://seed",
            position=i,
            metadata="{}",
        )
        for i in range(10)
    ]
    store.insert_chunks(seed)
    store.close()

    errors: list = []

    def _inserter():
        s = SQLiteChunkStore(db_path)
        s.open()
        s._conn.execute("PRAGMA busy_timeout=10000")
        for i in range(30):
            try:
                s.insert_chunks(
                    [
                        ChunkRecord(
                            chunk_id=f"ins-{i}",
                            document_id="doc-ins",
                            content=f"inserted content {i}",
                            source_uri="test://ins",
                            position=i,
                            metadata="{}",
                        )
                    ]
                )
            except sqlite3.OperationalError:
                pass
        s.close()

    def _searcher(tid: int):
        s = SQLiteChunkStore(db_path)
        s.open()
        s._conn.execute("PRAGMA busy_timeout=10000")
        for _ in range(15):
            try:
                s.search("searchable content", limit=5)
            except sqlite3.OperationalError:
                pass
            except Exception as exc:
                errors.append((tid, exc))
        s.close()

    threads = [threading.Thread(target=_inserter)]
    threads += [threading.Thread(target=_searcher, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == [], f"Search errors during concurrent insert: {errors}"


def test_preferences_concurrent_save_load(tmp_path: Path) -> None:
    """Multiple threads save/load preferences — no corruption."""
    path = tmp_path / "config" / "preferences.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Initialize
    prefs = UserPreferences()
    prefs.save(path)

    errors: list = []
    barrier = threading.Barrier(6)

    def _writer(idx: int):
        barrier.wait()
        for i in range(10):
            p = UserPreferences.load(path)
            p.merge({"custom_instructions": f"thread-{idx}-iter-{i}"})
            p.save(path)

    def _reader(idx: int):
        barrier.wait()
        for _ in range(10):
            try:
                p = UserPreferences.load(path)
                # Must be a valid instance regardless of concurrent writes
                assert isinstance(p.language, str)
            except Exception as exc:
                errors.append((idx, exc))

    threads = [threading.Thread(target=_writer, args=(i,)) for i in range(3)]
    threads += [threading.Thread(target=_reader, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert errors == [], f"Preference read errors: {errors}"
    # Final load should succeed and be valid
    final = UserPreferences.load(path)
    assert isinstance(final.custom_instructions, str)
