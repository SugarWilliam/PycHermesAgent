import json

from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService
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
