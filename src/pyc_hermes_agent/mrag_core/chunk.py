"""Chunking helpers for text-oriented MRAG."""

from __future__ import annotations

import re
from typing import List

from pyc_hermes_agent.contracts import DocumentChunk, KnowledgeDocument

# Plain text emitted by pptx_extractor: ``[Slide N]`` / ``[Notes N]`` blocks separated by ``\n\n``.
_PPTX_BLOCK_HEADER = re.compile(r"\[(Slide|Notes) (\d+)\]\n", flags=re.IGNORECASE)


def chunk_document(document: KnowledgeDocument, *, chunk_size: int = 500, overlap: int = 100) -> List[DocumentChunk]:
    text = document.text.strip()
    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if document.source_type == "pptx":
        return _chunk_pptx(document, text, chunk_size=chunk_size, overlap=overlap)
    return _chunk_linear(document, text, chunk_size=chunk_size, overlap=overlap)


def _chunk_linear(
    document: KnowledgeDocument,
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> List[DocumentChunk]:
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
                DocumentChunk(document_id=document.document_id, index=index, text=chunk_text, metadata=metadata),
            )
            index += 1
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _chunk_pptx(
    document: KnowledgeDocument,
    full_text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> List[DocumentChunk]:
    matches = list(_PPTX_BLOCK_HEADER.finditer(full_text))
    if not matches:
        return _chunk_linear(document, full_text, chunk_size=chunk_size, overlap=overlap)

    out: List[DocumentChunk] = []
    chunk_index = 0
    for i, m in enumerate(matches):
        block_kind = m.group(1).lower()
        block_num = int(m.group(2))
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block_body = full_text[body_start:body_end].strip()
        if not block_body:
            continue
        body_len = len(block_body)
        local_start = 0
        while local_start < body_len:
            local_end = min(body_len, local_start + chunk_size)
            chunk_text = block_body[local_start:local_end].strip()
            if chunk_text:
                g_start = body_start + local_start
                g_end = body_start + local_end
                metadata = dict(document.metadata)
                meta_patch: dict = {
                    "start": g_start,
                    "end": g_end,
                    "title": document.title,
                    "source_uri": document.source_uri,
                    "source_type": document.source_type,
                    "page": None,
                    "section": f"{block_kind}-{block_num}",
                    "pptx_block_kind": block_kind,
                    "pptx_block_number": block_num,
                }
                if block_kind == "slide":
                    meta_patch["slide"] = block_num
                metadata.update(meta_patch)
                out.append(
                    DocumentChunk(document_id=document.document_id, index=chunk_index, text=chunk_text, metadata=metadata),
                )
                chunk_index += 1
            if local_end == body_len:
                break
            local_start = local_end - overlap
    return out
