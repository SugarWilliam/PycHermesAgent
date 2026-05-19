# Phase 3E1 - PPT Authoring Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3E_PPT_XLSX_Authoring_Plan_v0.3.0.md`
**Goal:** Add a presentation-generation path that can turn structured agent output into readable `.pptx` artifacts through the existing artifact engine.

---

## 1. Scope

Phase 3E1 isolates PowerPoint generation as its own implementation track.

In scope:

- `.pptx` exporter MVP
- slide data model
- template and theme baseline
- sidecar integration for PPT export requests
- desktop artifact visibility for presentations

Out of scope:

- advanced animation
- SmartArt parity
- embedded macros
- full designer-grade slide editing

---

## 2. Current Baseline

Current completed baseline includes:

- generic artifact export via `ArtifactEngine`
- artifact listing via sidecar `/artifacts`
- desktop shell capable of artifact-oriented context display

Current gap:

- no `.pptx` writer exists
- no presentation-specific artifact metadata exists
- no flow turns agent summaries/tables/charts into slides

---

## 3. Architecture Rules

- PPT creation belongs to `artifact_engine`, not `mrag_core`.
- Generated presentations are runtime artifacts, not knowledge-base content.
- Presentation generation must produce standard `.pptx` files and remain deterministic enough for tests.

---

## 4. Workstreams

### P1. Slide Data Model

Target files:

- new `src/pyc_hermes_agent/artifact_engine/pptx_types.py`
- `src/pyc_hermes_agent/artifact_engine/__init__.py`

Required outcomes:

- Typed structures for title, agenda, content, table, and chart slides.
- Clear separation between content model and file-writing implementation.

### P2. PPTX Exporter MVP

Target files:

- new `src/pyc_hermes_agent/artifact_engine/pptx_exporter.py`
- optional template assets under `src/pyc_hermes_agent/artifact_engine/templates/pptx/*`

Required outcomes:

- Generate valid `.pptx` files.
- Support core slide types defined in the MVP.

### P3. Prompt-to-Presentation Flow

Target files:

- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`

Required outcomes:

- Structured agent output can be mapped into slide content.
- Presentation export request can be triggered from chat results.

### P4. Desktop Presentation Artifact UX

Target files:

- `desktop/src/components/layout/ContextPanel.jsx`
- `desktop/src/services/sidecarClient.js`

Required outcomes:

- `.pptx` artifacts are clearly identified and inspectable in the desktop.

---

## 5. Test Plan

Target tests:

- new `tests/contract/test_pptx_exporter.py`
- updates to `tests/contract/test_artifact_engine.py`
- updates to `tests/contract/test_sidecar_api.py`

Required verification:

- generated `.pptx` exists and is structurally valid
- artifact metadata is preserved
- sidecar can list the generated presentation

---

## 6. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Slide scope expands too quickly | Delivery delay | Strict MVP slide types only |
| Generated deck is unreadable | Poor UX | Product-owned templates and formatting defaults |

---

## 7. Exit Definition

Phase 3E1 is complete when:

- Agent can generate a valid, readable `.pptx` artifact from structured output.
- Presentation artifacts are visible through sidecar and desktop artifact views.

---
