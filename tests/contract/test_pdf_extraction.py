"""Contract tests for PDF text extraction — no pymupdf required."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from pyc_hermes_agent.mrag_core.parse import parse_text_document
from pyc_hermes_agent.mrag_core.pdf_extractor import (
    PDFExtractionResult,
    PDFPage,
    extract_pdf,
)


def test_extract_pdf_raises_without_library():
    """If neither pymupdf nor pdfplumber is installed, clear ImportError."""
    with patch.dict(sys.modules, {"fitz": None, "pdfplumber": None}):
        with pytest.raises(ImportError, match="Install pymupdf or pdfplumber"):
            extract_pdf(__file__)  # type: ignore[arg-type]


def _make_result(pages: list[PDFPage]) -> PDFExtractionResult:
    total = sum(p.char_count for p in pages)
    return PDFExtractionResult(
        source_path="/tmp/test.pdf",
        title="Test Doc",
        page_count=len(pages),
        pages=pages,
        total_chars=total,
    )


def test_pdf_extraction_result_to_chunks():
    """Mock PDFExtractionResult, verify chunking works."""
    pages = [PDFPage(page_number=1, text="A" * 500, char_count=500)]
    result = _make_result(pages)
    chunks = result.to_chunks(chunk_size=200, overlap=50)
    assert len(chunks) >= 1
    assert all("text" in c and "metadata" in c for c in chunks)


def test_chunks_have_page_metadata():
    """Each chunk has page number in metadata."""
    pages = [
        PDFPage(page_number=1, text="Hello world " * 50, char_count=600),
        PDFPage(page_number=2, text="Second page " * 50, char_count=600),
    ]
    result = _make_result(pages)
    chunks = result.to_chunks(chunk_size=200, overlap=50)
    for chunk in chunks:
        assert "page" in chunk["metadata"]
        assert chunk["metadata"]["page"] in (1, 2)
        assert chunk["metadata"]["source"] == "/tmp/test.pdf"


def test_chunks_respect_size_limit():
    """No chunk text exceeds chunk_size."""
    chunk_size = 300
    overlap = 50
    pages = [PDFPage(page_number=1, text="X" * 1000, char_count=1000)]
    result = _make_result(pages)
    chunks = result.to_chunks(chunk_size=chunk_size, overlap=overlap)
    for chunk in chunks:
        assert len(chunk["text"]) <= chunk_size


def test_empty_page_skipped():
    """Empty pages don't produce chunks."""
    pages = [
        PDFPage(page_number=1, text="", char_count=0),
        PDFPage(page_number=2, text="   ", char_count=3),
        PDFPage(page_number=3, text="Content here", char_count=12),
    ]
    result = _make_result(pages)
    chunks = result.to_chunks()
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["page"] == 3


def test_overlap_must_be_less_than_chunk_size():
    """ValueError if overlap >= chunk_size."""
    pages = [PDFPage(page_number=1, text="text", char_count=4)]
    result = _make_result(pages)
    with pytest.raises(ValueError, match="overlap must be smaller"):
        result.to_chunks(chunk_size=100, overlap=100)


def test_parse_text_document_preserves_caller_metadata():
    document = parse_text_document("hello", metadata={"page": 2, "section": "summary"})

    assert document.metadata["length"] == 5
    assert document.metadata["page"] == 2
    assert document.metadata["section"] == "summary"


def test_parse_text_document_keeps_computed_length_over_caller_value():
    document = parse_text_document("hello", metadata={"length": 999, "page": 2})

    assert document.metadata["length"] == 5
    assert document.metadata["page"] == 2
