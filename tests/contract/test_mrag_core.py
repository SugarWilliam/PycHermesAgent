from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService


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
