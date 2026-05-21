"""Chunking helpers for text-oriented MRAG."""

from __future__ import annotations

from typing import List

from pyc_hermes_agent.contracts import DocumentChunk, KnowledgeDocument


def chunk_document(document: KnowledgeDocument, *, chunk_size: int = 500, overlap: int = 100) -> List[DocumentChunk]:
    text = document.text.strip()
    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[DocumentChunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk_text = text[start:end].strip()
        if chunk_text:
            metadata = dict(document.metadata)
            metadata.update(
                {
                    "start": start,
                    "end": end,
                    "title": document.title,
                    "source_uri": document.source_uri,
                    "source_type": document.source_type,
                    "page": document.metadata.get("page"),
                    "section": document.metadata.get("section", ""),
                }
            )
            chunks.append(
                DocumentChunk(
                    document_id=document.document_id,
                    index=index,
                    text=chunk_text,
                    metadata=metadata,
                )
            )
            index += 1
        if end == len(text):
            break
        start = end - overlap
    return chunks
