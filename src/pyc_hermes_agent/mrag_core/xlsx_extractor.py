"""Extract plain text from Office Open XML (.xlsx) without third-party deps."""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def _t(local: str) -> str:
    return f"{{{_MAIN}}}{local}"


def extract_xlsx_plain_text(path: Path | str) -> str:
    """Return flattened text grouped by worksheet (``[SheetName]`` blocks)."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))

    try:
        with zipfile.ZipFile(resolved) as zf:
            shared = _shared_string_table(zf)
            targets = _list_worksheet_targets(zf)
            if not targets:
                raise ValueError(f"No worksheets found in: {resolved}")
            blocks: list[str] = []
            for sheet_name, member in targets:
                try:
                    body = zf.read(member).decode("utf-8")
                except KeyError:
                    continue
                grid = _extract_sheet_text(body, shared)
                if grid.strip():
                    blocks.append(f"[{sheet_name}]\n{grid}")
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid XLSX (not a ZIP archive): {resolved}") from exc

    return "\n\n".join(blocks).strip()


def _shared_string_table(zf: zipfile.ZipFile) -> list[str]:
    try:
        raw = zf.read("xl/sharedStrings.xml").decode("utf-8")
    except KeyError:
        return []

    root = ET.fromstring(raw)
    texts: list[str] = []
    for si in root.findall(f".//{_t('si')}"):
        parts: list[str] = []
        for node in si.findall(f".//{_t('t')}"):
            if node.text:
                parts.append(node.text)
            if node.tail:
                parts.append(node.tail)
        texts.append("".join(parts).strip())
    return texts


def _list_worksheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return ``(sheet_display_name, zip_member_path)`` in workbook order."""
    try:
        wb_raw = zf.read("xl/workbook.xml").decode("utf-8")
    except KeyError as exc:
        raise ValueError("Invalid XLSX (missing xl/workbook.xml)") from exc

    wb_root = ET.fromstring(wb_raw)
    sheets_el = wb_root.find(_t("sheets"))
    if sheets_el is None:
        return []

    order: list[tuple[str, str]] = []
    for sh in sheets_el.findall(_t("sheet")):
        name = sh.get("name") or "Sheet"
        rid = sh.get(f"{{{_REL}}}id")
        if rid:
            order.append((name, rid))

    rel_map = _workbook_rels(zf)
    resolved: list[tuple[str, str]] = []
    for name, rid in order:
        target = rel_map.get(rid)
        if not target:
            continue
        if "worksheets" not in target.replace("\\", "/"):
            continue
        if target not in zf.namelist():
            base = target.split("/")[-1]
            guess = f"xl/worksheets/{base}"
            if guess in zf.namelist():
                target = guess
            else:
                continue
        resolved.append((name, target))
    return resolved


def _workbook_rels(zf: zipfile.ZipFile) -> dict[str, str]:
    raw = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    root = ET.fromstring(raw)
    out: dict[str, str] = {}
    rel_tag = f"{{{_PKG_REL}}}Relationship"
    for rel in root.findall(rel_tag):
        rid = rel.get("Id")
        target = (rel.get("Target") or "").replace("\\", "/").lstrip("/")
        if not rid:
            continue
        if target.startswith("xl/"):
            path = target
        else:
            path = "xl/" + target
        out[rid] = path
    return out


def _extract_sheet_text(sheet_xml: str, shared: list[str]) -> str:
    root = ET.fromstring(sheet_xml)
    sd = root.find(_t("sheetData"))
    if sd is None:
        return ""

    lines_out: list[str] = []

    for row_el in sd.findall(_t("row")):
        row_cells: list[tuple[int, str]] = []

        for cell_el in row_el.findall(_t("c")):
            cref_raw = cell_el.get("r") or ""
            cref = cref_raw.upper().strip()
            if not cref:
                continue

            cref_match = re.match(r"^([A-Z]+)([0-9]+)$", cref)
            if not cref_match:
                continue
            col_letters = cref_match.group(1)

            ctype = cell_el.get("t")
            rendered = ""

            inner_is = cell_el.find(_t("is"))
            if inner_is is not None:
                for tnode in inner_is.findall(f".//{_t('t')}"):
                    if tnode.text:
                        rendered += tnode.text
                    if tnode.tail:
                        rendered += tnode.tail

            inner_v = cell_el.find(_t("v"))
            if not rendered and inner_v is not None and inner_v.text:
                raw_v = inner_v.text.strip()
                if ctype == "s":
                    idx = _safe_int(raw_v)
                    if idx is not None and 0 <= idx < len(shared):
                        rendered = shared[idx]
                else:
                    rendered = raw_v

            stripped = rendered.strip().replace("\t", " ").replace("\n", " ")
            if stripped:
                row_cells.append((_col_index_ord(col_letters), stripped))

        if not row_cells:
            continue

        row_cells.sort(key=lambda x: x[0])
        lines_out.append("\t".join(v for _, v in row_cells))

    return "\n".join(lines_out).strip()


def _col_index_ord(letters: str) -> int:
    acc = 0
    for ch in letters.upper():
        if not ch.isalpha():
            continue
        acc = acc * 26 + (ord(ch) - ord("A") + 1)
    return acc


def _safe_int(v: Any) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


__all__ = ["extract_xlsx_plain_text"]
