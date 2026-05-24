"""Minimal in-memory MRAG service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from pyc_hermes_agent.contracts import KnowledgeDocument, RetrievalRequest, RetrievalResult
from pyc_hermes_agent.mrag_core.chunk import chunk_document
from pyc_hermes_agent.mrag_core.document import KnowledgeBase
from pyc_hermes_agent.mrag_core.ownership import MRAGStorageOwner, acquire_mrag_storage_owner
from pyc_hermes_agent.mrag_core.parse import parse_file_document, parse_text_document, parse_url_document
from pyc_hermes_agent.mrag_core.persistence import load_knowledge_bases, persist_knowledge_base
from pyc_hermes_agent.mrag_core.retrieve import retrieve


class MRAGService:
    def __init__(self, *, storage_root: Path | None = None) -> None:
        self._storage_root = storage_root.resolve() if storage_root is not None else None
        self._storage_owner: MRAGStorageOwner | None = acquire_mrag_storage_owner(self._storage_root) if self._storage_root is not None else None
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}
        if self._storage_root is None:
            return
        try:
            self._knowledge_bases = load_knowledge_bases(self._storage_root)
        except Exception:
            if self._storage_owner is not None:
                self._storage_owner.close()
                self._storage_owner = None
            raise

    def create_knowledge_base(self, name: str) -> KnowledgeBase:
        kb = KnowledgeBase(knowledge_base_id=str(uuid4()), name=name)
        self._knowledge_bases[kb.knowledge_base_id] = kb
        self._persist(kb)
        return kb

    def get_knowledge_base(self, knowledge_base_id: str) -> Optional[KnowledgeBase]:
        return self._knowledge_bases.get(knowledge_base_id)

    def list_knowledge_bases(self) -> list[dict]:
        return [
            {
                "knowledge_base_id": kb.knowledge_base_id,
                "name": kb.name,
                "documents": len(kb.documents),
                "chunks": len(kb.chunks),
            }
            for kb in self._knowledge_bases.values()
        ]

    def ingest_text(
        self,
        knowledge_base_id: str,
        text: str,
        *,
        title: str = "",
        source_uri: str = "",
        source_type: str = "text",
        metadata: Mapping[str, Any] | None = None,
    ) -> KnowledgeDocument:
        kb = self._require_kb(knowledge_base_id)
        document = parse_text_document(
            text,
            title=title,
            source_uri=source_uri,
            source_type=source_type,
            metadata=metadata,
        )
        self._store_document(kb, document)
        return document

    def ingest_file(self, knowledge_base_id: str, path: Path) -> KnowledgeDocument:
        kb = self._require_kb(knowledge_base_id)
        document = parse_file_document(path)
        self._store_document(kb, document)
        return document

    def ingest_url_text(self, knowledge_base_id: str, url: str, text: str, *, title: str = "") -> KnowledgeDocument:
        kb = self._require_kb(knowledge_base_id)
        document = parse_url_document(url, text, title=title)
        self._store_document(kb, document)
        return document

    def search(self, knowledge_base_id: str, request: RetrievalRequest) -> RetrievalResult:
        kb = self._require_kb(knowledge_base_id)
        return retrieve(kb, request)

    def rebuild_chunk_index(self, knowledge_base_id: str) -> int:
        kb = self._require_kb(knowledge_base_id)
        kb.chunks.clear()
        for document in list(kb.documents.values()):
            kb.add_chunks(chunk_document(document))
        self._persist(kb)
        return len(kb.chunks)

    def _store_document(self, kb: KnowledgeBase, document: KnowledgeDocument) -> None:
        kb.add_document(document)
        kb.add_chunks(chunk_document(document))
        self._persist(kb)

    def _require_kb(self, knowledge_base_id: str) -> KnowledgeBase:
        kb = self.get_knowledge_base(knowledge_base_id)
        if kb is None:
            raise KeyError(f"Knowledge base not found: {knowledge_base_id}")
        return kb

    def _persist(self, knowledge_base: KnowledgeBase) -> None:
        if self._storage_root is None:
            return
        persist_knowledge_base(self._storage_root, knowledge_base)

    def close(self) -> None:
        if self._storage_owner is None:
            return
        self._storage_owner.close()
        self._storage_owner = None

    def __enter__(self) -> "MRAGService":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
