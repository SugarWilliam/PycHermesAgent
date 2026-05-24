import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService, MRAGManifestIncompatibleError, MRAGStorageLockedError
from pyc_hermes_agent.mrag_core.docx_extractor import extract_docx_plain_text
from pyc_hermes_agent.mrag_core.xlsx_extractor import extract_xlsx_plain_text
from pyc_hermes_agent.mrag_core.pdf_extractor import PDFExtractionResult, PDFPage
from pyc_hermes_agent.mrag_core.ownership import MRAG_LOCK_FILE
from pyc_hermes_agent.mrag_core.persistence import MRAG_INDEX_FORMAT_VERSION, MRAG_MANIFEST_VERSION
from pyc_hermes_agent.sidecar_api.services.mrag_service import ingest_pdf_document


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
    citation = result.citations[0]
    assert citation.source_type == "markdown"
    assert citation.relevance == pytest.approx(result.hits[0].score)
    assert citation.page is None
    assert citation.section == ""


def test_mrag_citations_preserve_source_anchor_fields() -> None:
    service = MRAGService()
    kb = service.create_knowledge_base("anchor-fields")
    service.ingest_text(
        kb.knowledge_base_id,
        "Evidence packaging should preserve source anchors.",
        title="Evidence Note",
        source_uri="memory://anchors/1",
        source_type="markdown",
        metadata={"page": "7", "section": " intro ", "label": "anchor-source"},
    )
    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="source anchors", top_k=2))

    assert result.hits
    assert result.hits[0].metadata["label"] == "anchor-source"
    assert result.citations
    cite = result.citations[0]
    assert cite.source_type == "markdown"
    assert cite.page == 7
    assert cite.section == "intro"
    assert cite.relevance > 0.0


def test_mrag_pdf_ingest_preserves_page_provenance_in_citations(tmp_path) -> None:
    service = MRAGService()
    kb = service.create_knowledge_base("pdf-pages")
    extracted = PDFExtractionResult(
        source_path=str(tmp_path / "report.pdf"),
        title="Quarterly Report",
        page_count=1,
        pages=[PDFPage(page_number=3, text="Forecast evidence appears on this page.", char_count=38)],
        total_chars=38,
    )

    with patch("pyc_hermes_agent.mrag_core.pdf_extractor.extract_pdf", return_value=extracted):
        with patch("pyc_hermes_agent.sidecar_api.services.mrag_service._get_mrag_service", return_value=service):
            ingest_pdf_document(kb.knowledge_base_id, extracted.source_path)

    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="forecast evidence", top_k=3))

    assert result.citations
    cite = result.citations[0]
    assert cite.source_type == "pdf"
    assert cite.source_uri == extracted.source_path
    assert cite.page == 3
    assert cite.section == "page-3"


def test_mrag_docx_ingest_and_search_paragraph_text(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>MRAG DOCX ingestion overview.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Second paragraph for retrieval alpha.</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    docx_path = tmp_path / "note.docx"
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", xml)

    assert "DOCX ingestion" in extract_docx_plain_text(docx_path)

    service = MRAGService()
    kb = service.create_knowledge_base("docx-test")
    service.ingest_file(kb.knowledge_base_id, docx_path)

    stored = service.get_knowledge_base(kb.knowledge_base_id)
    assert stored is not None
    doc = next(iter(stored.documents.values()))
    assert doc.source_type == "docx"
    assert "alpha" in doc.text.lower()

    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="DOCX retrieval", top_k=3))
    assert result.hits
    assert result.citations
    assert result.citations[0].source_type == "docx"


def test_mrag_html_file_ingest_strips_markup_and_reads_title(tmp_path: Path) -> None:
    from pyc_hermes_agent.mrag_core.parse import parse_file_document

    html_body = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><title>MRAG HTML &amp; Title Track</title>
<script type="text/javascript">window.__evil_script_marker__()</script><style>p { display: none; }</style></head>
<body><p>Visible paragraph for HTML ingestion zeta token.</p></body></html>"""
    html_path = tmp_path / "page.html"
    html_path.write_text(html_body, encoding="utf-8")

    parsed = parse_file_document(html_path)
    assert parsed.source_type == "html"
    assert parsed.title == "MRAG HTML & Title Track"
    assert parsed.metadata.get("html_title") == "MRAG HTML & Title Track"
    assert "evil_script_marker" not in parsed.text.lower()
    assert "Visible paragraph for HTML ingestion zeta token" in parsed.text

    service = MRAGService(storage_root=tmp_path / "html-store")
    kb = service.create_knowledge_base("html-kb-id")
    service.ingest_file(kb.knowledge_base_id, html_path)
    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="HTML ingestion zeta", top_k=3))
    assert result.hits
    assert result.citations
    assert result.citations[0].source_type == "html"


def test_mrag_xlsx_ingest_and_search_shared_string(tmp_path: Path) -> None:
    workbook_xml = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="DemoSheet" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    shared_xml = """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="1" uniqueCount="1">
  <si><t>MRAG XLSX retrieval alpha token</t></si>
</sst>"""

    sheet_xml = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c></row>
  </sheetData>
</worksheet>"""

    xlsx_path = tmp_path / "grid.xlsx"

    with zipfile.ZipFile(xlsx_path, "w") as zf:
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)

        zf.writestr("xl/sharedStrings.xml", shared_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    assert "XLSX retrieval" in extract_xlsx_plain_text(xlsx_path)

    service = MRAGService()

    kb = service.create_knowledge_base("xlsx-test")
    service.ingest_file(kb.knowledge_base_id, xlsx_path)

    stored = service.get_knowledge_base(kb.knowledge_base_id)

    assert stored is not None

    doc = next(iter(stored.documents.values()))

    assert doc.source_type == "xlsx"
    assert "alpha" in doc.text.lower()

    result = service.search(kb.knowledge_base_id, RetrievalRequest(query="XLSX retrieval token", top_k=3))
    assert result.hits
    assert result.citations
    assert result.citations[0].source_type == "xlsx"


def test_extract_xlsx_rejects_bad_archive(tmp_path: Path) -> None:
    bad = tmp_path / "fake.xlsx"

    bad.write_text("not zip", encoding="utf-8")
    with pytest.raises(ValueError, match="ZIP archive"):
        extract_xlsx_plain_text(bad)


def test_extract_docx_rejects_bad_archive(tmp_path: Path) -> None:
    bad = tmp_path / "fake.docx"
    bad.write_text("not zip", encoding="utf-8")
    with pytest.raises(ValueError, match="ZIP archive"):
        extract_docx_plain_text(bad)


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

    manifest = json.loads((storage_root / "knowledge_bases" / kb.knowledge_base_id / "manifest.json").read_text(encoding="utf-8"))
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


def test_mrag_lexical_and_hybrid_can_rank_top_hit_differently(tmp_path: Path) -> None:
    """Hybrid (trigram semantic + lexical) must be able to change top-1 vs pure lexical."""
    service = MRAGService(storage_root=tmp_path / "rank")
    kb = service.create_knowledge_base("rank")
    doc_a = "AAA BBB common filler words alpha beta gamma delta epsilon zeta eta theta"
    doc_b = "unusualpatternZZZYYY isolated rare token corpus zzz yyy unusualpatternZZZYYY cluster"
    query = "AAA BBB unusualpatternZZZYYY"

    service.ingest_text(kb.knowledge_base_id, doc_a, title="lex-heavy", source_uri="memory://a", source_type="markdown")
    service.ingest_text(kb.knowledge_base_id, doc_b, title="hybrid-shift", source_uri="memory://b", source_type="markdown")

    lexical = service.search(kb.knowledge_base_id, RetrievalRequest(query=query, top_k=2, retrieval_mode="lexical"))
    hybrid = service.search(
        kb.knowledge_base_id,
        RetrievalRequest(query=query, top_k=2, retrieval_mode="hybrid", semantic_weight=0.65),
    )
    assert lexical.hits and hybrid.hits
    assert lexical.hits[0].document_id != hybrid.hits[0].document_id


def test_mrag_pptx_ingest_extracts_slide_text(tmp_path: Path) -> None:
    pytest.importorskip("pptx")
    from pptx import Presentation
    from pptx.util import Inches

    path = tmp_path / "deck.pptx"
    prs = Presentation()
    layout_idx = 6 if len(prs.slide_layouts) > 6 else max(0, len(prs.slide_layouts) - 1)
    layout = prs.slide_layouts[layout_idx]

    s1 = prs.slides.add_slide(layout)
    b1 = s1.shapes.add_textbox(Inches(0.5), Inches(1), Inches(8), Inches(1))
    b1.text_frame.text = "alpha onboarding MRAG pptx deck intro."

    s2 = prs.slides.add_slide(layout)
    b2 = s2.shapes.add_textbox(Inches(0.5), Inches(1), Inches(8), Inches(1))
    b2.text_frame.text = "gamma_secret_token_xyz slides body unique phrase."

    try:
        prs.slides[0].notes_slide.notes_text_frame.text = "PRIVATE_SPEAKER_NOTE_MARKER only in speaker notes pane."
    except Exception:
        pass

    prs.save(path)

    service = MRAGService(storage_root=tmp_path / "pptx-ingest")
    kb = service.create_knowledge_base("pptx-ingest-kb")
    doc = service.ingest_file(kb.knowledge_base_id, path)

    assert doc.source_type == "pptx"
    assert "[Slide 1]" in doc.text and "[Slide 2]" in doc.text

    r_slide2 = service.search(kb.knowledge_base_id, RetrievalRequest(query="gamma_secret_token_xyz", top_k=3))
    assert r_slide2.citations
    assert any(c.section == "slide-2" for c in r_slide2.citations)

    r_slide1 = service.search(kb.knowledge_base_id, RetrievalRequest(query="alpha onboarding pptx deck intro", top_k=3))
    assert r_slide1.citations
    assert any(c.section == "slide-1" for c in r_slide1.citations)

    rn = service.search(kb.knowledge_base_id, RetrievalRequest(query="PRIVATE_SPEAKER_NOTE_MARKER only", top_k=3))
    if rn.citations:
        assert any((c.section or "").startswith("notes-") for c in rn.citations)


def test_mrag_image_ingest_accepts_tesseract_output(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    pytest.importorskip("pytesseract")

    from PIL import Image

    img_path = tmp_path / "scan.png"
    Image.new("RGB", (16, 16), color=(240, 240, 240)).save(img_path)

    with patch("pytesseract.image_to_string", return_value="Captured OCR headline for ingest.\n"):
        service = MRAGService(storage_root=tmp_path / "img-ingest")
        kb = service.create_knowledge_base("ocr-kb")
        doc = service.ingest_file(kb.knowledge_base_id, img_path)

    assert doc.source_type == "image"
    assert "OCR headline" in doc.text

    hits = service.search(kb.knowledge_base_id, RetrievalRequest(query="OCR headline ingest", top_k=2))
    assert hits.hits


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
