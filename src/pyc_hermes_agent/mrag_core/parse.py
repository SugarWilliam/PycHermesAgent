"""Minimal text-oriented parsing for local-first MRAG."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from pyc_hermes_agent.contracts import KnowledgeDocument


_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp"})


def parse_text_document(
    text: str,
    *,
    title: str = "",
    source_uri: str = "",
    source_type: str = "text",
    metadata: Mapping[str, Any] | None = None,
) -> KnowledgeDocument:

    clean_text = text.strip()
    document_metadata = dict(metadata or {})
    document_metadata["length"] = len(clean_text)
    return KnowledgeDocument(
        title=title or _title_from_text(text),
        source_type=source_type,
        source_uri=source_uri,
        text=clean_text,
        metadata=document_metadata,
    )


def parse_file_document(path: Path) -> KnowledgeDocument:

    suffix = path.suffix.lower()

    handlers: dict[str, Callable[[Path], KnowledgeDocument]] = {
        ".docx": _parse_docx,
        ".xlsx": _parse_xlsx,
        ".pptx": _parse_pptx,
        ".html": _parse_html,
        ".htm": _parse_html,
    }

    if suffix in handlers:
        return handlers[suffix](path)

    if suffix in _IMAGE_SUFFIXES:
        return _parse_image(path)

    text = path.read_text(encoding="utf-8")

    source_type = {
        ".md": "markdown",
        ".txt": "text",
    }.get(suffix, "text")

    return parse_text_document(text, title=path.stem, source_uri=str(path), source_type=source_type)


def parse_url_document(url: str, text: str, *, title: str = "") -> KnowledgeDocument:

    return parse_text_document(text, title=title or url, source_uri=url, source_type="url")


def _parse_docx(path: Path) -> KnowledgeDocument:

    from pyc_hermes_agent.mrag_core.docx_extractor import extract_docx_plain_text

    text = extract_docx_plain_text(path)

    return parse_text_document(
        text,
        title=path.stem,
        source_uri=str(path.resolve()),
        source_type="docx",
        metadata={"format": "docx"},
    )


def _parse_xlsx(path: Path) -> KnowledgeDocument:

    from pyc_hermes_agent.mrag_core.xlsx_extractor import extract_xlsx_plain_text

    text = extract_xlsx_plain_text(path)

    return parse_text_document(
        text,
        title=path.stem,
        source_uri=str(path.resolve()),
        source_type="xlsx",
        metadata={"format": "xlsx"},
    )


def _parse_pptx(path: Path) -> KnowledgeDocument:

    from pyc_hermes_agent.mrag_core.pptx_extractor import extract_pptx_plain_text

    text = extract_pptx_plain_text(path)

    return parse_text_document(
        text,
        title=path.stem,
        source_uri=str(path.resolve()),
        source_type="pptx",
        metadata={"format": "pptx"},
    )


def _parse_html(path: Path) -> KnowledgeDocument:
    from pyc_hermes_agent.mrag_core.html_extractor import extract_html_for_ingest

    text, title = extract_html_for_ingest(path)

    metadata: dict[str, object] = {"format": "html"}
    if title:
        metadata["html_title"] = title

    return parse_text_document(
        text,
        title=title or path.stem,
        source_uri=str(path.resolve()),
        source_type="html",
        metadata=metadata,
    )


def _parse_image(path: Path) -> KnowledgeDocument:

    from pyc_hermes_agent.mrag_core.image_extractor import extract_image_plain_text

    text = extract_image_plain_text(path)

    return parse_text_document(
        text,
        title=path.stem,
        source_uri=str(path.resolve()),
        source_type="image",
        metadata={"format": path.suffix.lower().lstrip("."), "parser": "ocr"},
    )


def _title_from_text(text: str) -> str:

    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:120]

    return "untitled"
