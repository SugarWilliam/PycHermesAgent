"""MRAG knowledge base service functions."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Mapping

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService
from pyc_hermes_agent.sidecar_api.services.common import (
    _serialize,
    resolve_runtime_directories_root,
)


class MRAGServiceRegistry:
    """Thread-safe registry for MRAG service instances keyed by storage root."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._services: dict[str, MRAGService] = {}

    def get(self, root: Path | None = None) -> MRAGService:
        runtime_paths = ensure_runtime_directories(resolve_runtime_paths(resolve_runtime_directories_root(root)))
        storage_root = runtime_paths.mrag_dir
        cache_key = str(storage_root)
        with self._lock:
            service = self._services.get(cache_key)
            if service is None:
                service = MRAGService(storage_root=storage_root)
                self._services[cache_key] = service
            return service


_mrag_registry = MRAGServiceRegistry()


def _get_mrag_service(root: Path | None = None) -> MRAGService:
    return _mrag_registry.get(root)


def list_knowledge_bases(root: Path | None = None) -> List[Dict[str, Any]]:
    return _get_mrag_service(root).list_knowledge_bases()


def create_knowledge_base(name: str, root: Path | None = None) -> Dict[str, Any]:
    kb = _get_mrag_service(root).create_knowledge_base(name)
    return {
        "knowledge_base_id": kb.knowledge_base_id,
        "name": kb.name,
        "documents": 0,
        "chunks": 0,
    }


def ingest_text_document(
    knowledge_base_id: str,
    text: str,
    *,
    title: str = "",
    source_uri: str = "",
    source_type: str = "text",
    metadata: Mapping[str, Any] | None = None,
    root: Path | None = None,
) -> Dict[str, Any]:
    document = _get_mrag_service(root).ingest_text(
        knowledge_base_id,
        text,
        title=title,
        source_uri=source_uri,
        source_type=source_type,
        metadata=metadata,
    )
    return _serialize(document)


def materialize_text_document(
    knowledge_base_id: str,
    text: str,
    *,
    title: str = "",
    source_uri: str = "",
    root: Path | None = None,
) -> Dict[str, Any]:
    """Ingest finalized prose via the MRAG text path with materialization bookkeeping metadata."""

    return ingest_text_document(
        knowledge_base_id,
        text,
        title=title or "Materialized note",
        source_uri=source_uri or "memory://materialize",
        source_type="markdown",
        metadata={"pipeline": "materialize", "materialization": True},
        root=root,
    )


def ingest_pdf_document(
    knowledge_base_id: str,
    path: Path | str,
    *,
    title: str = "",
    chunk_size: int = 1000,
    overlap: int = 200,
    root: Path | None = None,
) -> Dict[str, Any]:
    from pyc_hermes_agent.mrag_core.pdf_extractor import extract_pdf

    result = extract_pdf(Path(path).expanduser(), title=title or None)
    chunks = result.to_chunks(chunk_size=chunk_size, overlap=overlap)
    service = _get_mrag_service(root)
    # Ingest each chunk as a text document with page metadata
    doc_ids: List[str] = []
    for chunk in chunks:
        chunk_metadata = dict(chunk["metadata"])
        page = chunk_metadata.get("page")
        if page is not None and not chunk_metadata.get("section"):
            chunk_metadata["section"] = f"page-{page}"
        doc = service.ingest_text(
            knowledge_base_id,
            chunk["text"],
            title=chunk["metadata"].get("title", ""),
            source_uri=result.source_path,
            source_type="pdf",
            metadata=chunk_metadata,
        )
        doc_ids.append(doc.document_id)
    return {
        "source_path": result.source_path,
        "title": result.title,
        "page_count": result.page_count,
        "total_chars": result.total_chars,
        "chunks_ingested": len(doc_ids),
        "extraction_errors": result.extraction_errors,
    }


def ingest_file_document(knowledge_base_id: str, path: Path | str, *, root: Path | None = None) -> Dict[str, Any]:
    document = _get_mrag_service(root).ingest_file(knowledge_base_id, Path(path).expanduser())
    return _serialize(document)


def ingest_url_document(
    knowledge_base_id: str,
    url: str,
    text: str,
    *,
    title: str = "",
    root: Path | None = None,
) -> Dict[str, Any]:
    document = _get_mrag_service(root).ingest_url_text(knowledge_base_id, url, text, title=title)
    return _serialize(document)


def search_knowledge_base(knowledge_base_id: str, request: RetrievalRequest, root: Path | None = None) -> Dict[str, Any]:
    result = _get_mrag_service(root).search(knowledge_base_id, request)
    return _serialize(result)


def rebuild_mrag_chunk_index(knowledge_base_id: str, root: Path | None = None) -> Dict[str, Any]:
    count = _get_mrag_service(root).rebuild_chunk_index(knowledge_base_id)
    return {"knowledge_base_id": knowledge_base_id, "chunk_count": count, "status": "rebuilt"}
