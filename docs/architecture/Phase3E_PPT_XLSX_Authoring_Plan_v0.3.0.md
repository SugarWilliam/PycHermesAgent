# Phase 3E - PPT and XLSX Authoring Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Extend the artifact system from generic file export into first-class business-output generation for PowerPoint and Excel deliverables.

---

## 1. Scope

Phase 3E turns existing artifact foundations into usable authoring capabilities.

In scope:

- PPTX generation MVP
- XLSX generation MVP
- export templates and styling conventions
- artifact listing and desktop visibility
- prompt-to-artifact workflow support

Out of scope:

- full office-suite templating platform
- arbitrary macro/script embedding
- storing generated artifacts inside MRAG
- replacing the artifact engine with a document store

---

## 2. Current Baseline

Current completed baseline includes:

- `ArtifactEngine` supports `export_bytes`, `export_text`, and `export_json`
- artifact metadata is checksum-protected and staging-promoted
- sidecar exposes `/artifacts`
- desktop can inspect artifact-oriented runtime context at a foundation level

Current gap:

- No typed PPTX or XLSX generator exists.
- Agent output is not yet transformable into office artifacts through a structured path.
- Artifact UX is still generic rather than business-document aware.

---

## 3. Architecture Rules

- Generated documents belong to `artifact_engine`, not `mrag_core`.
- Artifact metadata must remain versioned and integrity-checked.
- Generated files must be written under local runtime artifact paths, never install directories.
- Office authoring must not leak provider-native output objects into artifact internals.

---

## 4. Workstreams

### E1. Artifact Authoring Interfaces

**Goal:** create explicit export interfaces for office-style outputs.

Target files:

- `src/pyc_hermes_agent/artifact_engine/__init__.py`
- new `src/pyc_hermes_agent/artifact_engine/types.py` if needed
- `src/pyc_hermes_agent/sidecar_api/services/common.py`

Required outcomes:

- Artifact export supports typed office-document requests.
- Metadata can distinguish generated PPTX/XLSX from generic binary exports.

Acceptance:

- Sidecar and runtime can request office exports in a structured way.

### E2. PPTX Generator MVP

**Goal:** support basic presentation creation.

Target files:

- new `src/pyc_hermes_agent/artifact_engine/pptx_exporter.py`
- new optional `src/pyc_hermes_agent/artifact_engine/templates/pptx/*`
- sidecar integration files under `src/pyc_hermes_agent/sidecar_api/services/*`

Required outcomes:

- Supports title slides, agenda slides, content slides, table slides, and chart slides.
- Generated PPTX is openable in standard PowerPoint-compatible software.

Acceptance:

- Agent can export a usable `.pptx` artifact.

### E3. XLSX Generator MVP

**Goal:** support basic workbook generation.

Target files:

- new `src/pyc_hermes_agent/artifact_engine/xlsx_exporter.py`
- new optional `src/pyc_hermes_agent/artifact_engine/templates/xlsx/*`
- sidecar integration files under `src/pyc_hermes_agent/sidecar_api/services/*`

Required outcomes:

- Supports tables, multiple sheets, summaries, and simple charts.
- Generated XLSX is openable in standard spreadsheet software.

Acceptance:

- Agent can export a usable `.xlsx` artifact.

### E4. Template and Styling Model

**Goal:** make outputs readable and product-consistent.

Target files:

- `src/pyc_hermes_agent/artifact_engine/templates/*`
- desktop rendering references if preview images/metadata are later added

Required outcomes:

- Product-owned styles exist for PPTX and XLSX outputs.
- Style choices remain simple, readable, and maintainable.

Acceptance:

- Generated documents look intentionally formatted, not raw dumps.

### E5. Prompt-to-Artifact Workflow

**Goal:** connect agent outputs to office exports in a usable flow.

Target files:

- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`

Required outcomes:

- Structured chat outputs can become export payloads.
- Agent can request export from an analyzed or summarized result.

Acceptance:

- User can ask for PPT/XLSX creation and receive artifact output in the product flow.

### E6. Desktop Artifact UX

**Goal:** make generated office files visible and usable from the desktop.

Target files:

- `desktop/src/components/layout/ContextPanel.jsx`
- `desktop/src/store/*`
- `desktop/src/services/sidecarClient.js`

Required outcomes:

- Artifact list clearly identifies PPTX and XLSX outputs.
- User can inspect filename, media type, size, and path.

Acceptance:

- Generated office artifacts are visible from the desktop context flow.

---

## 5. Execution Order

Recommended order:

1. E1 - Artifact Authoring Interfaces
2. E2 - PPTX Generator MVP
3. E3 - XLSX Generator MVP
4. E4 - Template and Styling Model
5. E5 - Prompt-to-Artifact Workflow
6. E6 - Desktop Artifact UX

---

## 6. Test Plan

Required verification:

- artifact engine tests for PPTX/XLSX generation
- openability sanity checks for generated files
- sidecar artifact listing tests
- desktop artifact visibility tests where available

Target test areas:

- `tests/contract/test_artifact_engine.py`
- new `tests/contract/test_pptx_exporter.py`
- new `tests/contract/test_xlsx_exporter.py`
- `tests/contract/test_sidecar_api.py`
- `tests/contract/test_sidecar_http.py`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Office export scope explodes | Delivery delay | Keep strict MVP scope |
| Generated files are technically valid but unreadable | Poor UX | Product-owned templates and sanity checks |
| Artifacts bleed into retrieval storage | Boundary violation | Keep all exports in `artifact_engine` only |

---

## 8. Exit Definition

Phase 3E is complete when:

- Agent can generate basic `.pptx` and `.xlsx` artifacts.
- Artifacts are versioned, listed, and visible in desktop context.
- Output quality is readable and consistent with product expectations.

---
