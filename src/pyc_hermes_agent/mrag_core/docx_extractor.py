"""Extract plain text from Office Open XML (.docx) without third-party deps.

DOCX is a ZIP archive; body text lives in ``word/document.xml`` as ``w:p`` /
``w:t`` nodes (WordprocessingML).
"""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_XMLNS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_docx_plain_text(path: Path | str) -> str:
    """Return UTF-8 safe plain text grouped by paragraphs."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    try:
        with zipfile.ZipFile(resolved) as zf:
            try:
                xml_bytes = zf.read("word/document.xml")
            except KeyError as exc:
                raise ValueError(f"Invalid DOCX (missing word/document.xml): {resolved}") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid DOCX (not a ZIP archive): {resolved}") from exc

    root = ET.fromstring(xml_bytes)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", _XMLNS):
        chunks: list[str] = []
        for node in paragraph.findall(".//w:t", _XMLNS):
            if node.text:
                chunks.append(node.text)
        line = "".join(chunks).strip()
        if line:
            paragraphs.append(line)

    return "\n\n".join(paragraphs).strip()


__all__ = ["extract_docx_plain_text"]
