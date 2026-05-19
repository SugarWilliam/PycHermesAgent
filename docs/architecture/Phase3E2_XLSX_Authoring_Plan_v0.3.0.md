# Phase 3E2 - XLSX Authoring Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3E_PPT_XLSX_Authoring_Plan_v0.3.0.md`
**Goal:** Add workbook-generation support so the agent can export structured tables, summaries, and simple charts into `.xlsx` artifacts using the existing artifact pipeline.

---

## 1. Scope

Phase 3E2 isolates spreadsheet generation as its own implementation track.

In scope:

- `.xlsx` exporter MVP
- workbook and worksheet data model
- simple formatting and chart support
- sidecar integration for workbook export
- desktop artifact visibility for spreadsheets

Out of scope:

- advanced spreadsheet formulas beyond MVP needs
- macros and embedded code
- full spreadsheet editing UI inside the desktop

---

## 2. Current Baseline

Current completed baseline includes:

- generic artifact export via `ArtifactEngine`
- artifact listing APIs
- no typed spreadsheet export capability yet

Current gap:

- no `.xlsx` writer exists
- no workbook/sheet export model exists
- no direct pathway from structured results to spreadsheet artifacts

---

## 3. Architecture Rules

- Spreadsheet export belongs to `artifact_engine`, not MRAG.
- Generated `.xlsx` files must remain standard and openable in normal spreadsheet software.
- Spreadsheet export metadata remains under artifact version control.

---

## 4. Workstreams

### X1. Workbook Data Model

Target files:

- new `src/pyc_hermes_agent/artifact_engine/xlsx_types.py`
- `src/pyc_hermes_agent/artifact_engine/__init__.py`

Required outcomes:

- Typed structures for workbook, worksheet, table region, and simple chart region.

### X2. XLSX Exporter MVP

Target files:

- new `src/pyc_hermes_agent/artifact_engine/xlsx_exporter.py`
- optional template assets under `src/pyc_hermes_agent/artifact_engine/templates/xlsx/*`

Required outcomes:

- Generate valid `.xlsx` files.
- Support multi-sheet export and simple charts.

### X3. Prompt-to-Workbook Flow

Target files:

- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`

Required outcomes:

- Structured result tables can be transformed into workbook exports.

### X4. Desktop Spreadsheet Artifact UX

Target files:

- `desktop/src/components/layout/ContextPanel.jsx`
- `desktop/src/services/sidecarClient.js`

Required outcomes:

- `.xlsx` artifacts are clearly labeled and inspectable.

---

## 5. Test Plan

Target tests:

- new `tests/contract/test_xlsx_exporter.py`
- updates to `tests/contract/test_artifact_engine.py`
- updates to `tests/contract/test_sidecar_api.py`

Required verification:

- generated `.xlsx` exists and is structurally valid
- workbook metadata survives artifact listing

---

## 6. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Spreadsheet scope expands into full BI export | Delivery delay | Keep MVP focused on tables and simple charts |
| Generated sheet layout is hard to read | Poor UX | Product-owned sheet formatting defaults |

---

## 7. Exit Definition

Phase 3E2 is complete when:

- Agent can generate a valid, readable `.xlsx` artifact from structured output.
- Spreadsheet artifacts are visible through sidecar and desktop artifact views.

---
