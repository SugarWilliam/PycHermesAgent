"""Contract tests for PPTX slide → notes coupling via OOXML relationships."""

from __future__ import annotations

import zipfile
from pathlib import Path

from pyc_hermes_agent.mrag_core.pptx_extractor import extract_pptx_plain_text

_CTYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>
"""

_RELS_NOTE_TO_SLIDE99 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rN1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
    Target="../notesSlides/notesSlide99.xml"/>
</Relationships>
"""

_PRES_REL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
    Target="slides/slide1.xml"/>
</Relationships>
"""

_PRESENTATION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId1"/>
  </p:sldIdLst>
</p:presentation>
"""

_SLIDE_BODY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
      <p:sp><p:txBody><a:p><a:r><a:t>slide visible token alpha</a:t></a:r></a:p></p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""

_NOTE_BODY = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:notes xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
      <p:sp><p:txBody><a:p><a:r><a:t>notes_linked_via_rels_marker_qz9</a:t></a:r></a:p></p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:notes>
"""


def test_notes_index_follows_slide_deck_position_not_notes_filename_suffix(tmp_path: Path) -> None:
    pptx_path = tmp_path / "minimal.pptx"
    with zipfile.ZipFile(pptx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", _CTYPES)
        zf.writestr("ppt/_rels/presentation.xml.rels", _PRES_REL)
        zf.writestr("ppt/presentation.xml", _PRESENTATION)
        zf.writestr("ppt/slides/slide1.xml", _SLIDE_BODY)
        zf.writestr("ppt/slides/_rels/slide1.xml.rels", _RELS_NOTE_TO_SLIDE99)
        zf.writestr("ppt/notesSlides/notesSlide99.xml", _NOTE_BODY)

    text = extract_pptx_plain_text(pptx_path)
    assert "[Slide 1]" in text and "slide visible token alpha" in text
    assert "[Notes 1]" in text and "notes_linked_via_rels_marker_qz9" in text
    assert "[Notes 99]" not in text
    pos_slide = text.index("[Slide 1]")
    pos_notes = text.index("[Notes 1]")
    assert pos_slide < pos_notes


def test_slide_without_notes_rels_skips_notes_block(tmp_path: Path) -> None:
    pres_only = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
    Target="slides/slide1.xml"/>
</Relationships>
"""
    pptx_path = tmp_path / "no_notes_rels.pptx"
    with zipfile.ZipFile(pptx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", _CTYPES)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_only)
        zf.writestr("ppt/presentation.xml", _PRESENTATION)
        zf.writestr("ppt/slides/slide1.xml", _SLIDE_BODY)

    text = extract_pptx_plain_text(pptx_path)
    assert "[Slide 1]" in text
    assert "[Notes " not in text
