"""Minimal in-memory MRAG service."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from pyc_hermes_agent.contracts import KnowledgeDocument, RetrievalRequest, RetrievalResult
from pyc_hermes_agent.mrag_core.chunk import chunk_document
from pyc_hermes_agent.mrag_core.document import KnowledgeBase
from pyc_hermes_agent.mrag_core.parse import parse_file_document, parse_text_document, parse_url_document
from pyc_hermes_agent.mrag_core.persistence import load_knowledge_bases, persist_knowledge_base
from pyc_hermes_agent.mrag_core.retrieve import retrieve


class MRAGService:
    def __init__(self, *, storage_root: Path | None = None) -> None:
        self._storage_root = storage_root.resolve() if storage_root is not None else None
        self._knowledge_bases: Dict[str, KnowledgeBase] = (
            load_knowledge_bases(self._storage_root) if self._storage_root is not None else {}
        )

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

    def ingest_text(self, knowledge_base_id: str, text: str, *, title: str = "", source_uri: str = "", source_type: str = "text") -> KnowledgeDocument:
        kb = self._require_kb(knowledge_base_id)
        document = parse_text_document(text, title=title, source_uri=source_uri, source_type=source_type)
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
