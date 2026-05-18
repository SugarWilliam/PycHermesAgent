import json
from pathlib import Path

import pytest

from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService, MRAGManifestIncompatibleError, MRAGStorageLockedError
from pyc_hermes_agent.mrag_core.ownership import MRAG_LOCK_FILE
from pyc_hermes_agent.mrag_core.persistence import MRAG_INDEX_FORMAT_VERSION, MRAG_MANIFEST_VERSION


def test_mrag_ingest_and_search_text() -> None:
    service = MRAGService()
    kb = service.create_knowledge_base("demo")
    service.ingest_text(
        kb.knowledge_base_id,
        "# Forecasting Notes\nDeepSeek and forecasting quality depend on context and evidence packaging.",
        title="Forecasting Notes",
        source_uri="memory://demo/1",
        source_type="markdown",
    )
    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="forecasting evidence", top_k=3))
    assert result.hits
    assert result.citations
    assert result.coverage > 0


def test_mrag_lists_knowledge_bases() -> None:
    service = MRAGService()
    service.create_knowledge_base("kb-a")
    service.create_knowledge_base("kb-b")
    bases = service.list_knowledge_bases()
    assert len(bases) == 2


def test_mrag_chunking_happens_on_ingest() -> None:
    service = MRAGService()
    kb = service.create_knowledge_base("chunk-test")
    service.ingest_text(kb.knowledge_base_id, "A" * 1200, title="Long Text")
    stored = service.get_knowledge_base(kb.knowledge_base_id)
    assert stored is not None
    assert len(stored.chunks) >= 2


def test_mrag_persists_knowledge_bases_across_service_restarts(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    first_service = MRAGService(storage_root=storage_root)
    kb = first_service.create_knowledge_base("persisted")
    first_service.ingest_text(
        kb.knowledge_base_id,
        "MetaHarness selects methods and MRAG packages evidence with citations.",
        title="Persisted Note",
        source_uri="memory://persisted/1",
    )

    second_service = MRAGService(storage_root=storage_root)
    persisted = second_service.get_knowledge_base(kb.knowledge_base_id)
    result = second_service.search(kb.knowledge_base_id, RetrievalRequest(query="evidence citations", top_k=2))

    assert persisted is not None
    assert persisted.name == "persisted"
    assert persisted.documents
    assert persisted.chunks
    assert result.hits


def test_mrag_persistence_writes_manifest_and_index_versions(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    service = MRAGService(storage_root=storage_root)
    kb = service.create_knowledge_base("versioned")
    service.ingest_text(
        kb.knowledge_base_id,
        "Versioned persistence keeps runtime state explicit.",
        title="Versioned Note",
        source_uri="memory://versioned/1",
    )

    manifest = json.loads(
        (storage_root / "knowledge_bases" / kb.knowledge_base_id / "manifest.json").read_text(encoding="utf-8")
    )
    chunks_payload = json.loads((storage_root / "indexes" / kb.knowledge_base_id / "chunks.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == MRAG_MANIFEST_VERSION
    assert manifest["index_format_version"] == MRAG_INDEX_FORMAT_VERSION
    assert manifest["document_count"] == 1
    assert manifest["chunk_count"] == len(chunks_payload["chunks"])
    assert chunks_payload["index_format_version"] == MRAG_INDEX_FORMAT_VERSION
    assert chunks_payload["chunks"]


def test_mrag_loads_legacy_chunk_index_list_shape(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    first_service = MRAGService(storage_root=storage_root)
    kb = first_service.create_knowledge_base("legacy")
    first_service.ingest_text(
        kb.knowledge_base_id,
        "Legacy chunk payloads should still load after format markers are added.",
        title="Legacy Note",
        source_uri="memory://legacy/1",
    )

    chunks_path = storage_root / "indexes" / kb.knowledge_base_id / "chunks.json"
    current_payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks_path.write_text(json.dumps(current_payload["chunks"], ensure_ascii=True, indent=2), encoding="utf-8")

    second_service = MRAGService(storage_root=storage_root)
    persisted = second_service.get_knowledge_base(kb.knowledge_base_id)
    result = second_service.search(kb.knowledge_base_id, RetrievalRequest(query="format markers", top_k=2))

    assert persisted is not None
    assert persisted.chunks
    assert result.hits


def test_mrag_ingests_file_and_url_text(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    source_path = tmp_path / "source.md"
    source_path.write_text("# File Source\nMRAG file ingest preserves source evidence.", encoding="utf-8")
    service = MRAGService(storage_root=storage_root)
    kb = service.create_knowledge_base("sources")

    file_document = service.ingest_file(kb.knowledge_base_id, source_path)
    url_document = service.ingest_url_text(
        kb.knowledge_base_id,
        "https://example.invalid/mrag",
        "URL ingest preserves remote evidence text for retrieval.",
        title="Remote Source",
    )
    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="evidence retrieval", top_k=5))

    assert file_document.source_type == "markdown"
    assert url_document.source_type == "url"
    assert {citation.source_uri for citation in result.citations} >= {str(source_path), "https://example.invalid/mrag"}


def test_mrag_rejects_storage_root_locked_by_unknown_owner(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    storage_root.mkdir()
    (storage_root / MRAG_LOCK_FILE).write_text(
        json.dumps({"owner_id": "external-owner", "pid": 999999}, ensure_ascii=True),
        encoding="utf-8",
    )

    with pytest.raises(MRAGStorageLockedError) as exc_info:
        MRAGService(storage_root=storage_root)

    assert str(storage_root) in str(exc_info.value)
    assert exc_info.value.lock_path == storage_root / MRAG_LOCK_FILE


def test_mrag_allows_same_process_to_share_storage_owner(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    first_service = MRAGService(storage_root=storage_root)
    kb = first_service.create_knowledge_base("shared")

    second_service = MRAGService(storage_root=storage_root)
    persisted = second_service.get_knowledge_base(kb.knowledge_base_id)

    assert persisted is not None
    assert persisted.name == "shared"


def test_mrag_rejects_manifest_newer_than_runtime(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    service = MRAGService(storage_root=storage_root)
    kb = service.create_knowledge_base("future")
    service.ingest_text(kb.knowledge_base_id, "hello", title="t")
    service.close()

    manifest_path = storage_root / "knowledge_bases" / kb.knowledge_base_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_version"] = MRAG_MANIFEST_VERSION + 99
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")

    with pytest.raises(MRAGManifestIncompatibleError) as exc:
        MRAGService(storage_root=storage_root)
    assert exc.value.knowledge_base_id == kb.knowledge_base_id


def test_mrag_rejects_chunk_index_newer_than_runtime(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    service = MRAGService(storage_root=storage_root)
    kb = service.create_knowledge_base("future-chunks")
    service.ingest_text(kb.knowledge_base_id, "hello", title="t")
    service.close()

    chunks_path = storage_root / "indexes" / kb.knowledge_base_id / "chunks.json"
    payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    payload["index_format_version"] = MRAG_INDEX_FORMAT_VERSION + 99
    chunks_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    with pytest.raises(MRAGManifestIncompatibleError):
        MRAGService(storage_root=storage_root)


def test_mrag_rebuild_chunk_index_from_sources(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    service = MRAGService(storage_root=storage_root)
    kb = service.create_knowledge_base("rebuild-me")
    service.ingest_text(kb.knowledge_base_id, "alpha beta gamma " * 200, title="long")
    kb_loaded = service.get_knowledge_base(kb.knowledge_base_id)
    assert kb_loaded is not None
    original_count = len(kb_loaded.chunks)
    kb_loaded.chunks.clear()
    assert len(kb_loaded.chunks) == 0
    service._persist(kb_loaded)

    same_service = MRAGService(storage_root=storage_root)
    assert len(same_service.get_knowledge_base(kb.knowledge_base_id).chunks) == 0
    rebuilt = same_service.rebuild_chunk_index(kb.knowledge_base_id)
    assert rebuilt == len(same_service.get_knowledge_base(kb.knowledge_base_id).chunks)
    assert rebuilt == original_count
    result = same_service.search(kb.knowledge_base_id, RetrievalRequest(query="gamma", top_k=3))
    assert result.hits


def test_mrag_close_releases_storage_owner(tmp_path) -> None:
    storage_root = tmp_path / "mrag-store"
    service = MRAGService(storage_root=storage_root)
    assert (storage_root / MRAG_LOCK_FILE).exists()

    service.close()

    assert not (storage_root / MRAG_LOCK_FILE).exists()
    replacement = MRAGService(storage_root=storage_root)
    replacement.create_knowledge_base("replacement")


def test_mrag_semantic_retrieval_returns_hits(tmp_path) -> None:
    service = MRAGService(storage_root=tmp_path / "sem")
    kb = service.create_knowledge_base("sem")
    service.ingest_text(kb.knowledge_base_id, "The quick brown fox jumps over the lazy dog.", title="animals")
    result = service.search(
        kb.knowledge_base_id,
        RetrievalRequest(query="quick fox jumping", top_k=2, retrieval_mode="semantic"),
    )
    assert result.hits
    assert any("trigram" in w.lower() for w in result.warnings)


def test_mrag_hybrid_retrieval_combines_signals(tmp_path) -> None:
    service = MRAGService(storage_root=tmp_path / "hyb")
    kb = service.create_knowledge_base("hyb")
    service.ingest_text(kb.knowledge_base_id, "alpha beta gamma delta", title="doc-a")
    service.ingest_text(kb.knowledge_base_id, "omega psi tau rho", title="doc-b")
    hybrid = service.search(
        kb.knowledge_base_id,
        RetrievalRequest(query="alpha gamma", top_k=2, retrieval_mode="hybrid", semantic_weight=0.5),
    )
    lexical = service.search(
        kb.knowledge_base_id,
        RetrievalRequest(query="alpha gamma", top_k=2, retrieval_mode="lexical"),
    )
    assert hybrid.hits and lexical.hits
    assert any("hybrid" in w.lower() for w in hybrid.warnings)


def test_mrag_unknown_retrieval_mode_returns_warning() -> None:
    service = MRAGService()
    kb = service.create_knowledge_base("bad-mode")
    service.ingest_text(kb.knowledge_base_id, "hello world", title="t")
    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="hello", retrieval_mode="quantum"))
    assert result.warnings
    assert not result.hits


def test_mrag_migrate_plan_detects_future_index_format(tmp_path) -> None:
    from pyc_hermes_agent.mrag_core.migrate import plan_migrations

    kb_root = tmp_path / "store" / "knowledge_bases" / "kb1"
    kb_root.mkdir(parents=True)
    (kb_root / "manifest.json").write_text(
        json.dumps(
            {
                "knowledge_base_id": "kb1",
                "name": "x",
                "manifest_version": 1,
                "index_format_version": MRAG_INDEX_FORMAT_VERSION + 50,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    notes = plan_migrations(tmp_path / "store")
    assert any("blocked" in n.lower() for n in notes)


def test_mrag_migrate_backup_copies_storage_tree(tmp_path) -> None:
    from pyc_hermes_agent.mrag_core import migrate as migrate_mod

    store = tmp_path / "mrag_storage"
    (store / "knowledge_bases" / "k1").mkdir(parents=True)
    marker = store / ".sentinel"
    marker.write_bytes(b"z")

    backup_parent = tmp_path / "backups"
    assert migrate_mod.main([str(store), "--backup-to", str(backup_parent)]) == 0
    created = sorted(backup_parent.glob("mrag_backup_*"))
    assert len(created) == 1
    blob = created[0] / ".sentinel"
    assert blob.read_bytes() == b"z"


def test_mrag_migrate_json_reports_backup_when_requested(tmp_path, capsys) -> None:
    from pyc_hermes_agent.mrag_core import migrate as migrate_mod

    store = tmp_path / "stor"
    store.mkdir()
    bk = tmp_path / "bk"
    assert migrate_mod.main([str(store), "--json", "--backup-to", str(bk)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "backup_path" in out
    assert Path(out["backup_path"]).exists()
