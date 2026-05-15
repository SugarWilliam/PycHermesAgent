"""Document models and in-memory knowledge base state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from pyc_hermes_agent.contracts import DocumentChunk, KnowledgeDocument


@dataclass(slots=True)
class KnowledgeBase:
    knowledge_base_id: str
    name: str
    documents: Dict[str, KnowledgeDocument] = field(default_factory=dict)
    chunks: List[DocumentChunk] = field(default_factory=list)

    def add_document(self, document: KnowledgeDocument) -> None:
        self.documents[document.document_id] = document

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        self.chunks.extend(chunks)
