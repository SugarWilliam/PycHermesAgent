"""Minimal JSON persistence for local-first MRAG state."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pyc_hermes_agent.contracts import DocumentChunk, KnowledgeDocument
from pyc_hermes_agent.mrag_core.document import KnowledgeBase


MRAG_MANIFEST_VERSION = 1
MRAG_INDEX_FORMAT_VERSION = 1


class MRAGManifestIncompatibleError(RuntimeError):
    """Raised when on-disk manifest or chunk index is newer than this runtime supports."""

    def __init__(self, knowledge_base_id: str, message: str) -> None:
        self.knowledge_base_id = knowledge_base_id
        super().__init__(message)


def _normalize_manifest_versions(manifest: dict[str, Any]) -> tuple[int, int]:
    raw_mv = manifest.get("manifest_version", 1)
    raw_iv = manifest.get("index_format_version", 1)
    try:
        mv = int(raw_mv) if raw_mv is not None else 1
    except (TypeError, ValueError) as exc:
        raise MRAGManifestIncompatibleError(
            str(manifest.get("knowledge_base_id") or ""),
            f"Invalid manifest_version: {raw_mv!r}",
        ) from exc
    try:
        iv = int(raw_iv) if raw_iv is not None else 1
    except (TypeError, ValueError) as exc:
        raise MRAGManifestIncompatibleError(
            str(manifest.get("knowledge_base_id") or ""),
            f"Invalid index_format_version in manifest: {raw_iv!r}",
        ) from exc
    if mv < 1:
        mv = 1
    if iv < 1:
        iv = 1
    return mv, iv


def _validate_manifest_for_load(knowledge_base_id: str, manifest: dict[str, Any]) -> None:
    mv, iv = _normalize_manifest_versions(manifest)
    if mv > MRAG_MANIFEST_VERSION:
        raise MRAGManifestIncompatibleError(
            knowledge_base_id,
            f"manifest_version {mv} exceeds supported {MRAG_MANIFEST_VERSION}; upgrade the application.",
        )
    if iv > MRAG_INDEX_FORMAT_VERSION:
        raise MRAGManifestIncompatibleError(
            knowledge_base_id,
            f"index_format_version {iv} in manifest exceeds supported {MRAG_INDEX_FORMAT_VERSION}; upgrade the application.",
        )


def _validate_chunks_file_for_load(knowledge_base_id: str, raw_chunks_payload: Any) -> None:
    if isinstance(raw_chunks_payload, dict):
        v = raw_chunks_payload.get("index_format_version")
        if v is None:
            return
        try:
            iv = int(v)
        except (TypeError, ValueError) as exc:
            raise MRAGManifestIncompatibleError(
                knowledge_base_id,
                f"Invalid index_format_version in chunks.json: {v!r}",
            ) from exc
        if iv > MRAG_INDEX_FORMAT_VERSION:
            raise MRAGManifestIncompatibleError(
                knowledge_base_id,
                f"chunks.json index_format_version {iv} exceeds supported {MRAG_INDEX_FORMAT_VERSION}; upgrade the application.",
            )


def load_knowledge_bases(storage_root: Path) -> dict[str, KnowledgeBase]:
    manifests_root = storage_root / "knowledge_bases"
    sources_root = storage_root / "sources"
    indexes_root = storage_root / "indexes"

    if not manifests_root.exists():
        return {}

    knowledge_bases: dict[str, KnowledgeBase] = {}
    for manifest_path in sorted(manifests_root.glob("*/manifest.json")):
        manifest = _read_json(manifest_path)
        if not isinstance(manifest, dict):
            continue
        knowledge_base_id = str(manifest.get("knowledge_base_id", ""))
        if not knowledge_base_id:
            continue

        _validate_manifest_for_load(knowledge_base_id, manifest)

        documents: dict[str, KnowledgeDocument] = {}
        for document_path in sorted((sources_root / knowledge_base_id).glob("*.json")):
            document = KnowledgeDocument(**_read_json(document_path))
            documents[document.document_id] = document

        chunks_path = indexes_root / knowledge_base_id / "chunks.json"
        chunks = []
        if chunks_path.exists():
            raw_chunks = _read_json(chunks_path)
            _validate_chunks_file_for_load(knowledge_base_id, raw_chunks)
            chunks = [DocumentChunk(**chunk) for chunk in _read_chunk_payload(raw_chunks)]

        knowledge_bases[knowledge_base_id] = KnowledgeBase(
            knowledge_base_id=knowledge_base_id,
            name=str(manifest.get("name", "")),
            documents=documents,
            chunks=chunks,
        )

    return knowledge_bases


def persist_knowledge_base(storage_root: Path, knowledge_base: KnowledgeBase) -> None:
    manifest_dir = storage_root / "knowledge_bases" / knowledge_base.knowledge_base_id
    sources_dir = storage_root / "sources" / knowledge_base.knowledge_base_id
    indexes_dir = storage_root / "indexes" / knowledge_base.knowledge_base_id

    manifest_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)
    indexes_dir.mkdir(parents=True, exist_ok=True)

    _write_json_atomic(
        manifest_dir / "manifest.json",
        {
            "manifest_version": MRAG_MANIFEST_VERSION,
            "index_format_version": MRAG_INDEX_FORMAT_VERSION,
            "knowledge_base_id": knowledge_base.knowledge_base_id,
            "name": knowledge_base.name,
            "document_count": len(knowledge_base.documents),
            "chunk_count": len(knowledge_base.chunks),
        },
    )

    current_document_paths = set()
    for document in knowledge_base.documents.values():
        document_path = sources_dir / f"{document.document_id}.json"
        current_document_paths.add(document_path)
        _write_json_atomic(document_path, asdict(document))

    for existing_path in sources_dir.glob("*.json"):
        if existing_path not in current_document_paths:
            existing_path.unlink()

    _write_json_atomic(
        indexes_dir / "chunks.json",
        {
            "index_format_version": MRAG_INDEX_FORMAT_VERSION,
            "chunks": [asdict(chunk) for chunk in knowledge_base.chunks],
        },
    )


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_chunk_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [chunk for chunk in payload if isinstance(chunk, dict)]
    if isinstance(payload, dict):
        chunks = payload.get("chunks", [])
        if isinstance(chunks, list):
            return [chunk for chunk in chunks if isinstance(chunk, dict)]
    return []


def _write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(path)


__all__ = [
    "MRAG_INDEX_FORMAT_VERSION",
    "MRAG_MANIFEST_VERSION",
    "MRAGManifestIncompatibleError",
    "load_knowledge_bases",
    "persist_knowledge_base",
]
