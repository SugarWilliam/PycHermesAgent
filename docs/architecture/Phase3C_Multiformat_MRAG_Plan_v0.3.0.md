# Phase 3C - Multiformat MRAG Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Expand MRAG from text/PDF-oriented retrieval into a broader document-intelligence subsystem supporting multiple business formats while preserving local-first evidence boundaries.

---

## 1. Scope

Phase 3C extends `mrag_core` ingestion, parsing, metadata, and citation handling.

In scope:

- `html` ingest
- `docx` ingest
- `xlsx` ingest
- `pptx` ingest
- image ingest through OCR-first extraction
- parser registry unification
- richer citation metadata across formats
- sidecar and desktop support for those richer sources

Out of scope:

- mixing artifacts into MRAG storage
- direct assignment of evidence grades inside `mrag_core`
- full multimedia reasoning beyond text-extracted evidence
- unbounded parser/plugin execution model

---

## 2. Current Baseline

Current completed baseline includes:

- text ingestion
- file ingestion
- URL text ingestion
- PDF extraction via `pdf_extractor.py`
- SQLite/FTS5 chunk storage
- lexical/hybrid retrieval foundations
- citation UI in the desktop

Current gap:

- No first-class support for `html`, `docx`, `xlsx`, `pptx`, or images.
- Citation metadata is still too shallow for sheet/slide/section-rich retrieval.
- Parser responsibilities are not yet structured for many formats.

---

## 3. Architecture Rules

- All document parsing remains inside `mrag_core`.
- Sidecar exposes ingest/search routes; desktop does not parse business files directly.
- MRAG remains evidence packaging only. It must not perform grading or method validity claims.
- Storage changes must preserve manifest/index compatibility rules.
- Richer citation metadata must not break existing retrieval consumers without versioning discipline.

---

## 4. Workstreams

### C1. Parser Registry Refactor

**Goal:** centralize format dispatch before adding more formats.

Target files:

- `src/pyc_hermes_agent/mrag_core/parse.py`
- `src/pyc_hermes_agent/mrag_core/service.py`
- new `src/pyc_hermes_agent/mrag_core/parsers/*`

Required outcomes:

- Format-specific logic is no longer ad hoc.
- Parser selection is deterministic by file/media type.
- Future formats can be added without bloating a single file.

Acceptance:

- Existing text/file/url/pdf ingestion still works through the refactored dispatch path.

### C2. HTML Ingest

**Goal:** support HTML documents and cleaned page-body extraction.

Target files:

- new `src/pyc_hermes_agent/mrag_core/parsers/html_extractor.py`
- `src/pyc_hermes_agent/mrag_core/parse.py`
- `src/pyc_hermes_agent/sidecar_api/services/mrag_service.py`

Required outcomes:

- HTML title and cleaned content extracted.
- Source URI and format metadata preserved.
- Citations can identify HTML source.

Acceptance:

- HTML content becomes searchable and cited correctly.

### C3. DOCX Ingest

**Goal:** support Word-format business documents.

Target files:

- new `src/pyc_hermes_agent/mrag_core/parsers/docx_extractor.py`
- `src/pyc_hermes_agent/mrag_core/parse.py`
- `src/pyc_hermes_agent/mrag_core/document.py`

Required outcomes:

- Headings, paragraphs, and table text extracted.
- Citation metadata preserves section-level provenance when possible.

Acceptance:

- DOCX documents are ingestible, searchable, and citeable.

### C4. XLSX Ingest

**Goal:** support workbook and sheet-oriented evidence extraction.

Target files:

- new `src/pyc_hermes_agent/mrag_core/parsers/xlsx_extractor.py`
- `src/pyc_hermes_agent/mrag_core/document.py`
- `src/pyc_hermes_agent/mrag_core/chunk.py`

Required outcomes:

- Workbook text is flattened into searchable chunks.
- Sheet names and positional context are preserved in metadata.
- Citation UI can show workbook/sheet provenance.

Acceptance:

- XLSX files can be searched and cited by sheet.

### C5. PPTX Ingest

**Goal:** support presentation documents as evidence sources.

Target files:

- new `src/pyc_hermes_agent/mrag_core/parsers/pptx_extractor.py`
- `src/pyc_hermes_agent/mrag_core/document.py`
- `src/pyc_hermes_agent/mrag_core/chunk.py`

Required outcomes:

- Slide titles, body text, and notes extracted where feasible.
- Citation metadata preserves slide number and title.

Acceptance:

- PPTX files are ingestible with usable slide-level citations.

### C6. Image OCR Ingest

**Goal:** support images as searchable evidence via OCR-first extraction.

Target files:

- new `src/pyc_hermes_agent/mrag_core/parsers/image_extractor.py`
- `src/pyc_hermes_agent/mrag_core/parse.py`
- `src/pyc_hermes_agent/sidecar_api/services/mrag_service.py`

Required outcomes:

- Supported image files can be ingested.
- OCR text and source metadata preserved.
- Failure states are explicit when OCR backends are missing.

Acceptance:

- Image-derived text becomes searchable with traceable source metadata.

### C7. Citation Metadata Upgrade

**Goal:** improve evidence fidelity across all formats.

Target files:

- `src/pyc_hermes_agent/mrag_core/document.py`
- `src/pyc_hermes_agent/mrag_core/chunk.py`
- `src/pyc_hermes_agent/mrag_core/sqlite_store.py`
- `desktop/src/components/context/CitationList.jsx`

Required outcomes:

- Chunk metadata can hold page / sheet / slide / section / source-type data.
- Desktop citation UI can display the richer origin fields.
- Storage layout/versioning is updated if required.

Acceptance:

- Users can tell exactly where evidence came from across supported formats.

### C8. Sidecar and Route Expansion

**Goal:** expose new ingest paths safely through the existing sidecar API.

Target files:

- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `src/pyc_hermes_agent/sidecar_api/services/mrag_service.py`
- `src/pyc_hermes_agent/sidecar_api/service.py`

Required outcomes:

- New formats are ingestible via explicit sidecar routes or format-aware file ingest.
- Structured errors cover unsupported formats and parser dependency issues.

Acceptance:

- Sidecar contracts remain stable while supporting richer ingest behavior.

### C9. Migration and Compatibility Safety

**Goal:** preserve persistence and release discipline while expanding MRAG.

Target files:

- `src/pyc_hermes_agent/mrag_core/migrate.py`
- `src/pyc_hermes_agent/mrag_core/migrate_to_sqlite.py`
- `docs/architecture/Compatibility_Matrix.md`
- `tests/contract/test_mrag_migration.py`

Required outcomes:

- Any on-disk metadata changes are versioned.
- Rebuild and migration rules are documented.
- Older knowledge bases fail safely when unsupported.

Acceptance:

- MRAG storage evolution remains compatible with project governance rules.

---

## 5. Execution Order

Recommended order:

1. C1 - Parser Registry Refactor
2. C2 - HTML Ingest
3. C3 - DOCX Ingest
4. C4 - XLSX Ingest
5. C5 - PPTX Ingest
6. C6 - Image OCR Ingest
7. C7 - Citation Metadata Upgrade
8. C8 - Sidecar and Route Expansion
9. C9 - Migration and Compatibility Safety

Rationale:

- Parser registry must stabilize before many formats are layered on top.
- Citation metadata should mature before declaring multi-format support complete.

---

## 6. Test Plan

Required verification:

- per-format parser tests
- sidecar ingest contract tests
- citation fidelity tests
- restart/reload tests if chunk metadata or storage format changes
- migration tests if manifest/index versions change

Target test areas:

- new `tests/contract/test_html_extraction.py`
- new `tests/contract/test_docx_extraction.py`
- new `tests/contract/test_xlsx_extraction.py`
- new `tests/contract/test_pptx_extraction.py`
- new `tests/contract/test_image_extraction.py`
- `tests/contract/test_mrag_sqlite.py`
- `tests/contract/test_mrag_migration.py`
- `tests/contract/test_sidecar_http.py`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Parser sprawl makes MRAG brittle | Maintenance cost and regressions | Central parser registry and focused extractor modules |
| Richer metadata breaks storage compatibility | KB migration issues | Explicit format/index versioning |
| OCR dependencies are fragile on Windows | Partial feature failure | Optional backend strategy + structured dependency errors |
| Citation fidelity regresses as formats expand | Loss of evidence trust | Contract tests for source provenance fields |

---

## 8. Exit Definition

Phase 3C is complete when:

- MRAG supports at least `html`, `docx`, `xlsx`, `pptx`, `image`, `pdf`, `text`, and `url`.
- Citation metadata remains source-faithful across all supported formats.
- Sidecar routes and storage compatibility rules remain controlled and testable.

---
