"""PDF text extraction with page-level chunking for MRAG ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PDFPage:
    page_number: int
    text: str
    char_count: int


@dataclass
class PDFExtractionResult:
    source_path: str
    title: str
    page_count: int
    pages: List[PDFPage]
    total_chars: int
    extraction_errors: List[str] = field(default_factory=list)

    def to_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> List[dict]:
        """Convert pages to overlapping text chunks suitable for MRAG ingestion.

        Returns list of dicts: {"text": ..., "metadata": {"page": N, "source": ...}}
        """
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        chunks: List[dict] = []
        for page in self.pages:
            text = page.text.strip()
            if not text:
                continue
            start = 0
            while start < len(text):
                end = min(len(text), start + chunk_size)
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(
                        {
                            "text": chunk_text,
                            "metadata": {
                                "page": page.page_number,
                                "source": self.source_path,
                                "title": self.title,
                            },
                        }
                    )
                if end == len(text):
                    break
                start = end - overlap
        return chunks


def _extract_with_fitz(path: Optional[Path], data: Optional[bytes], title: str) -> PDFExtractionResult:
    """Extract using pymupdf (fitz)."""
    import fitz

    if data is not None:
        doc = fitz.open(stream=data, filetype="pdf")
    else:
        doc = fitz.open(str(path))

    pages: List[PDFPage] = []
    errors: List[str] = []
    total_chars = 0

    for i in range(len(doc)):
        try:
            page = doc[i]
            text = page.get_text() or ""
            pages.append(PDFPage(page_number=i + 1, text=text, char_count=len(text)))
            total_chars += len(text)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Page {i + 1}: {exc}")

    doc.close()
    source = str(path) if path else title
    return PDFExtractionResult(
        source_path=source,
        title=title,
        page_count=len(doc) if not pages else len(pages),
        pages=pages,
        total_chars=total_chars,
        extraction_errors=errors,
    )


def _extract_with_pdfplumber(path: Optional[Path], data: Optional[bytes], title: str) -> PDFExtractionResult:
    """Extract using pdfplumber."""
    import io

    import pdfplumber

    open_arg = io.BytesIO(data) if data is not None else str(path)
    pages: List[PDFPage] = []
    errors: List[str] = []
    total_chars = 0

    with pdfplumber.open(open_arg) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
                pages.append(PDFPage(page_number=i + 1, text=text, char_count=len(text)))
                total_chars += len(text)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Page {i + 1}: {exc}")

    source = str(path) if path else title
    return PDFExtractionResult(
        source_path=source,
        title=title,
        page_count=len(pages),
        pages=pages,
        total_chars=total_chars,
        extraction_errors=errors,
    )


def _do_extract(path: Optional[Path], data: Optional[bytes], title: str) -> PDFExtractionResult:
    """Try pymupdf first, then pdfplumber, else raise ImportError."""
    try:
        return _extract_with_fitz(path, data, title)
    except ImportError:
        pass
    try:
        return _extract_with_pdfplumber(path, data, title)
    except ImportError:
        pass
    raise ImportError("Install pymupdf or pdfplumber for PDF support: pip install pymupdf")


def extract_pdf(path: Path, *, title: Optional[str] = None) -> PDFExtractionResult:
    """Extract text from a PDF file, page by page."""
    resolved = Path(path).expanduser().resolve()
    return _do_extract(resolved, None, title or resolved.name)


def extract_pdf_bytes(data: bytes, *, title: str = "untitled.pdf") -> PDFExtractionResult:
    """Extract from in-memory PDF bytes."""
    return _do_extract(None, data, title)
