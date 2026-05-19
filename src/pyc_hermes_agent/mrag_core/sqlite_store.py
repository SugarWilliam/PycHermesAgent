"""SQLite/FTS5 storage backend for MRAG knowledge bases."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ChunkRecord:
    """A single chunk stored in the SQLite database."""

    chunk_id: str
    document_id: str
    content: str
    source_uri: str
    position: int
    metadata: str  # JSON string


class SQLiteChunkStore:
    """FTS5-backed chunk storage for a single knowledge base."""

    SCHEMA_VERSION = 2  # Bump from JSON-era version 1

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        """Open connection and ensure schema."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._db_path), check_same_thread=False
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def close(self) -> None:
        """Close connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def insert_chunks(self, chunks: List[ChunkRecord]) -> int:
        """Bulk insert chunks. Returns count inserted."""
        assert self._conn is not None
        rows = [
            (c.chunk_id, c.document_id, c.content, c.source_uri, c.position, c.metadata)
            for c in chunks
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO chunks "
            "(chunk_id, document_id, content, source_uri, position, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def search(self, query: str, limit: int = 10) -> List[ChunkRecord]:
        """FTS5 full-text search. Returns ranked results."""
        assert self._conn is not None
        if not query or not query.strip():
            return []
        # Escape FTS5 operators by wrapping in double quotes
        escaped = '"' + query.replace('"', '""') + '"'
        cur = self._conn.execute(
            "SELECT c.chunk_id, c.document_id, c.content, "
            "c.source_uri, c.position, c.metadata "
            "FROM chunks_fts f "
            "JOIN chunks c ON f.rowid = c.rowid "
            "WHERE chunks_fts MATCH ? "
            "ORDER BY bm25(chunks_fts) "
            "LIMIT ?",
            (escaped, limit),
        )
        return [
            ChunkRecord(
                chunk_id=row[0],
                document_id=row[1],
                content=row[2],
                source_uri=row[3],
                position=row[4],
                metadata=row[5],
            )
            for row in cur.fetchall()
        ]

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        assert self._conn is not None
        cur = self._conn.execute(
            "DELETE FROM chunks WHERE document_id = ?", (document_id,)
        )
        self._conn.commit()
        return cur.rowcount

    def count(self) -> int:
        """Total chunk count."""
        assert self._conn is not None
        cur = self._conn.execute("SELECT COUNT(*) FROM chunks")
        return cur.fetchone()[0]

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def _ensure_schema(self) -> None:
        """Create tables, FTS index, and triggers if needed."""
        assert self._conn is not None
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                source_uri TEXT DEFAULT '',
                position INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                content='chunks',
                content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content)
                VALUES('delete', old.rowid, old.content);
            END;

            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(self.SCHEMA_VERSION)),
        )
        self._conn.commit()
