"""Minimal JSON persistence for local-first MRAG state."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pyc_hermes_agent.contracts import DocumentChunk, KnowledgeDocument
from pyc_hermes_agent.mrag_core.document import KnowledgeBase


def load_knowledge_bases(storage_root: Path) -> dict[str, KnowledgeBase]:
    manifests_root = storage_root / "knowledge_bases"
    sources_root = storage_root / "sources"
    indexes_root = storage_root / "indexes"

    if not manifests_root.exists():
        return {}

    knowledge_bases: dict[str, KnowledgeBase] = {}
    for manifest_path in sorted(manifests_root.glob("*/manifest.json")):
        manifest = _read_json(manifest_path)
        knowledge_base_id = str(manifest.get("knowledge_base_id", ""))
        if not knowledge_base_id:
            continue

        documents: dict[str, KnowledgeDocument] = {}
        for document_path in sorted((sources_root / knowledge_base_id).glob("*.json")):
            document = KnowledgeDocument(**_read_json(document_path))
            documents[document.document_id] = document

        chunks_path = indexes_root / knowledge_base_id / "chunks.json"
        chunks = []
        if chunks_path.exists():
            chunks = [DocumentChunk(**chunk) for chunk in _read_json(chunks_path)]

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
            "knowledge_base_id": knowledge_base.knowledge_base_id,
            "name": knowledge_base.name,
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

    _write_json_atomic(indexes_dir / "chunks.json", [asdict(chunk) for chunk in knowledge_base.chunks])


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(path)


__all__ = ["load_knowledge_bases", "persist_knowledge_base"]
