"""Minimal text-oriented parsing for local-first MRAG."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from pyc_hermes_agent.contracts import KnowledgeDocument


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
    if suffix == ".docx":
        from pyc_hermes_agent.mrag_core.docx_extractor import extract_docx_plain_text

        text = extract_docx_plain_text(path)
        return parse_text_document(
            text,
            title=path.stem,
            source_uri=str(path.resolve()),
            source_type="docx",
            metadata={"format": "docx"},
        )

    if suffix == ".xlsx":
        from pyc_hermes_agent.mrag_core.xlsx_extractor import extract_xlsx_plain_text

        text = extract_xlsx_plain_text(path)
        return parse_text_document(
            text,
            title=path.stem,
            source_uri=str(path.resolve()),
            source_type="xlsx",
            metadata={"format": "xlsx"},
        )

    text = path.read_text(encoding="utf-8")
    source_type = {
        ".md": "markdown",
        ".txt": "text",
        ".html": "html",
        ".htm": "html",
    }.get(suffix, "text")
    return parse_text_document(text, title=path.stem, source_uri=str(path), source_type=source_type)


def parse_url_document(url: str, text: str, *, title: str = "") -> KnowledgeDocument:
    return parse_text_document(text, title=title or url, source_uri=url, source_type="url")


def _title_from_text(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:120]
    return "untitled"
