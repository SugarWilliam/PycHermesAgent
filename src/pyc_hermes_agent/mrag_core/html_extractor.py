"""Extract searchable plain text from HTML for MRAG (stdlib only)."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

_TITLE_RE = re.compile(r"<title[^>]*>([\s\S]*?)</title>", flags=re.IGNORECASE)
_SKIP_EMBED = frozenset({"script", "style", "noscript", "template", "iframe"})
_BLOCK_END_NEWLINE = frozenset(
    {
        "p",
        "div",
        "li",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "section",
        "article",
        "header",
        "footer",
        "main",
        "ul",
        "ol",
        "table",
        "blockquote",
        "pre",
    }
)


class VisibleHTMLExtractor(HTMLParser):
    """Accumulate visible text; skip script/style/embed; light block boundaries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._embed_depth = 0
        self._chunks: list[str] = []

    def collapsed_text(self) -> str:
        text = "".join(self._chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in _SKIP_EMBED:
            self._embed_depth += 1
            return
        if self._embed_depth == 0 and t == "br":
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _SKIP_EMBED and self._embed_depth > 0:
            self._embed_depth -= 1
        if self._embed_depth == 0 and t in _BLOCK_END_NEWLINE:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._embed_depth > 0:
            return
        chunk = data.strip()
        if not chunk:
            return
        if self._chunks and not self._chunks[-1].endswith(("\n", " ")):
            self._chunks.append(" ")
        self._chunks.append(chunk)


def extract_visible_body_html(html: str) -> str:
    parser = VisibleHTMLExtractor()
    parser.feed(html)
    parser.close()
    return parser.collapsed_text()


def _extract_document_title(html: str) -> str:
    match = _TITLE_RE.search(html)
    if not match:
        return ""
    inner = match.group(1)
    inner = re.sub(r"<[^>]+>", " ", inner)
    return unescape(inner).strip()


def extract_html_for_ingest(path: Path | str, *, encoding: str = "utf-8") -> tuple[str, str]:
    """Return ``(combined_text, html_title_fragment)`` with a single file read."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    raw = resolved.read_text(encoding=encoding, errors="replace")

    title = _extract_document_title(raw)
    body_text = extract_visible_body_html(raw)

    chunks = [segment for segment in (title.strip(), body_text.strip()) if segment]
    merged = "\n\n".join(chunks).strip()
    return merged, title


def extract_html_plain_text(path: Path | str, *, encoding: str = "utf-8") -> str:
    """Backward-compatible printable text extractor (title + visible body)."""
    combined, _title = extract_html_for_ingest(path, encoding=encoding)
    return combined


__all__ = ["VisibleHTMLExtractor", "extract_html_for_ingest", "extract_html_plain_text", "extract_visible_body_html"]
