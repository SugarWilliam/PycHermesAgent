"""Extract plain text from Office Open XML (.pptx) without third-party deps."""

from __future__ import annotations

import posixpath
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_DML_MAIN = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OFC_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PML_MAIN = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def extract_pptx_plain_text(path: Path | str) -> str:
    """
    Return slide body text grouped as ``[Slide N]`` blocks, optionally followed immediately by
    ``[Notes N]`` for that slide when OOXML slide relationships point to ``notesSlides/…``.
    Speaker notes are paired by parsing each slide part's ``_rels/slide*.xml.rels`` (Target is
    usually ``../notesSlides/notesSlideM.xml``, resolved relative to ``ppt/slides/``).

    Enumeration order follows ``presentation.xml`` ``sldIdLst`` — the same numbering as slides
    ``[Slide 1..N]`` (``N`` equals deck position, not necessarily the numeric suffix in filenames).
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    try:
        with zipfile.ZipFile(resolved) as zf:
            wb_rels = _workbook_slide_rels(zf)
            order = _slide_order(zf)
            if not order:
                raise ValueError(f"Invalid PPTX (no slides in presentation): {resolved}")

            chunks: list[str] = []

            for idx, rel_id in enumerate(order, start=1):
                target = wb_rels.get(rel_id)
                if not target:
                    continue
                slide_path_raw = _ppt_inner_path(zf, target)
                slide_part = _part_path_in_zip(zf, slide_path_raw)
                if slide_part is None:
                    continue
                try:
                    body = zf.read(slide_part).decode("utf-8")
                except KeyError:
                    continue

                slide_text = _text_from_slide_xml(body)
                if slide_text.strip():
                    chunks.append(f"[Slide {idx}]\n{slide_text.strip()}")

                notes_part = _notes_slide_part_via_relationships(zf, slide_part)
                if notes_part is None:
                    continue
                try:
                    nbody = zf.read(notes_part).decode("utf-8")
                except KeyError:
                    continue
                notes_text = _text_from_slide_xml(nbody)
                if notes_text.strip():
                    chunks.append(f"[Notes {idx}]\n{notes_text.strip()}")

            return "\n\n".join(chunks).strip()

    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid PPTX (not a ZIP archive): {resolved}") from exc


def _part_path_in_zip(zf: zipfile.ZipFile, path: str) -> str | None:
    normalized = path.replace("\\", "/")
    names = zf.namelist()
    if normalized in names:
        return normalized
    lower_hit = {(n.lower()): n for n in names}.get(normalized.lower())
    return lower_hit


def _rels_path_for_part(part_path: str) -> str:
    """Maps ``ppt/slides/slide1.xml`` → ``ppt/slides/_rels/slide1.xml.rels``."""
    normalized = part_path.replace("\\", "/")
    dirname, basename = posixpath.split(normalized)
    return f"{dirname}/_rels/{basename}.rels"


def _resolve_rel_target_relative_to_slide_dir(slide_part: str, target: str) -> str:
    """Resolve OOXML Relationship ``Target`` (often ``../notesSlides/notesSlide1.xml``) to a ZIP path."""
    slide_dir = posixpath.dirname(slide_part.replace("\\", "/"))
    return posixpath.normpath(posixpath.join(slide_dir, target))


def _notes_slide_part_via_relationships(zf: zipfile.ZipFile, slide_part: str) -> str | None:
    rel_logical = _rels_path_for_part(slide_part)
    rel_actual = _part_path_in_zip(zf, rel_logical)
    if rel_actual is None:
        return None
    try:
        raw = zf.read(rel_actual).decode("utf-8")
    except KeyError:
        return None
    root = ET.fromstring(raw)
    tag_rel = f"{{{_PKG_REL}}}Relationship"
    chosen_target: str | None = None
    for rel in root.findall(tag_rel):
        mode = rel.get("TargetMode") or ""
        if mode.casefold() == "external":
            continue
        rtype = (rel.get("Type") or "").strip()
        if not rtype.endswith("/notesSlide"):
            continue
        target = (rel.get("Target") or "").strip()
        if not target:
            continue
        chosen_target = target
        break

    if chosen_target is None:
        return None

    resolved = _resolve_rel_target_relative_to_slide_dir(slide_part, chosen_target)
    return _part_path_in_zip(zf, resolved)


def _workbook_slide_rels(zf: zipfile.ZipFile) -> dict[str, str]:
    raw = zf.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
    root = ET.fromstring(raw)
    out: dict[str, str] = {}
    tag = f"{{{_PKG_REL}}}Relationship"
    for rel in root.findall(tag):
        rid = rel.get("Id")
        target = (rel.get("Target") or "").replace("\\", "/").lstrip("/")
        if not rid or not target:
            continue
        full = target if target.startswith("ppt/") else "ppt/" + target
        norm = full.replace("\\", "/")
        segs = norm.split("/")
        if len(segs) >= 3 and segs[-2].lower() == "slides" and segs[-1].lower().startswith("slide"):
            out[rid] = norm

    return out


def _slide_order(zf: zipfile.ZipFile) -> list[str]:
    raw = zf.read("ppt/presentation.xml").decode("utf-8")
    root = ET.fromstring(raw)
    sld_lst = root.find(f"{_PML_MAIN}sldIdLst")
    if sld_lst is None:
        return []
    ids: list[str] = []
    for sld in sld_lst.findall(f"{_PML_MAIN}sldId"):
        rid = sld.get(f"{_OFC_REL_NS}id")
        if rid:
            ids.append(rid)
    return ids


def _ppt_inner_path(zf: zipfile.ZipFile, target: str) -> str:
    t = target.replace("\\", "/")
    if _part_path_in_zip(zf, t) is not None:
        return t
    base = t.split("/")[-1]
    guess = "ppt/slides/" + base
    if _part_path_in_zip(zf, guess) is not None:
        return guess
    return t


def _text_from_slide_xml(slide_xml: str) -> str:
    root = ET.fromstring(slide_xml)
    fragments: list[str] = []
    for t_el in root.iter(f"{_DML_MAIN}t"):
        if t_el.text:
            fragments.append(t_el.text)
        if t_el.tail:
            fragments.append(t_el.tail)

    collapsed = "".join(fragments)
    lines = []
    buf: list[str] = []
    for ch in collapsed:
        if ch in "\r\n":
            line = "".join(buf).strip()
            buf = []
            if line:
                lines.append(line)
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        lines.append(tail)

    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in out_lines:
            out_lines.append(stripped)

    return "\n".join(out_lines).strip()


__all__ = ["extract_pptx_plain_text"]
