# PycHermesAgent v0.3.0-preview.1 Release Notes (draft)

> Engineering preview draft. Regenerate the metadata block after the final release-prep commit and immediately before tagging.

## Build metadata

- **Draft generated (UTC):** 2026-05-19T11:34:47Z
- **Draft base commit:** `b8a842a` on `main`
- **Package `__version__`:** `0.3.0`
- **`sidecar_api_version`:** `0.6`

## Highlights

- Delivers the first usable local analysis workbench for `PycHermesAgent`.
- Adds a Dify-style Electron desktop shell with streaming chat and rich Markdown rendering.
- Upgrades MRAG chunk storage from JSON to SQLite/FTS5 with migration tooling.
- Strengthens MetaHarness with `analysis_mode`, analysis cards, and a 15-case external benchmark.

## User-Facing Changes

- New Electron desktop shell under `desktop/` using React 18 + `electron-vite`.
- Three-column chat UI with sessions, settings, theme toggle, slash commands, citations, and context panel.
- Streaming Markdown rendering with Shiki code highlight, Mermaid, ECharts, KaTeX, tables, and callouts.
- Formal analysis mode now emits analysis cards with method, grades, risks, and assumptions.
- Builtin skill management now includes 8 builtin skills and audit tracking.
- Sidecar adds preferences routes, PDF ingest route, skill audit route, and health state machine fields.

## Engineering Changes

- Split large backend modules: `hermes_engine/runtime.py` and `sidecar_api/service.py`.
- Added `UserPreferences` / memory layers support in `hermes_engine`.
- Added `SQLiteChunkStore` with FTS5 ranking and JSON-to-SQLite migration CLI.
- Added PDF extraction pipeline and citation UI surfaces.
- Added desktop updater wiring and verified desktop build/startup on a local disk copy.
- Corrected desktop sidecar default port to `8765` and inlined updater bootstrap into `desktop/electron/main.js`.

## Migration Notes

- MRAG chunk persistence baseline is now `index_format_version = 2` with SQLite/FTS5.
- Existing v1 JSON knowledge bases remain readable for migration and can be upgraded with `scripts/migrate_mrag_to_sqlite.py`.
- Sidecar API baseline is now `0.6`; clients reading health metadata or route inventory should consume the updated payloads.
- Desktop remains preview-grade and should be treated as a local workbench, not a production installer.

## Verification

- `python scripts/release_gates.py --no-pytest`
- `python -m pytest tests/contract tests/integration --tb=line -q --ignore=tests/contract/test_sidecar_http.py`
- Result: `284 passed, 1 skipped`
- Desktop verification: `electron-vite build` succeeds on local disk; Electron launches successfully against a mock sidecar with SSE streaming.

## Known Limitations

- The repository is still not production-ready.
- Desktop packaging is preview-only: no code signing, no verified installer/upgrade path on clean Windows machines.
- Neural embeddings and full production semantic retrieval are not implemented yet.
- `tests/contract/test_sidecar_http.py` remains unsuitable as a release gate on the current SMB-backed workspace because of HTTP timeout/flakiness in this environment; release tagging should rely on the proven contract/integration suite above unless that environment issue is eliminated.
- Final tag metadata and this document's build block must be regenerated after the last release-prep commit.

## Recent Commits

```text
b8a842a fix(desktop): inline updater into main.js, fix sidecar port to 8765
654688d v0.3.0: Phase 2 complete - usable local analysis workbench with desktop shell
b7294d5 v0.2.1: fact-checked reassessment, Phase 2 GA draft, Windows sidecar PyInstaller release
3928344 Raise release gates toward GA: sidecar file logs, migrate backup, SBOM, desktop linux zip.
a5c6e17 Production path: hybrid MRAG retrieval, observability hooks, desktop pack gate.
f653087 Close Phase 1 engineering preview: skill audit on AgentLoop start, docs exit.
69b5ca9 Quality: Ruff E/W+F, mypy-clean src, CI gates; desktop sidecar spawn hardening.
29c26cf MetaHarness routing policies, SR grading, and CI hardening.
b429803 Health payload: python_version/platform; desktop shows runtime + refresh time.
0dbc29b Add preview release-notes generator and gate integration.
```
