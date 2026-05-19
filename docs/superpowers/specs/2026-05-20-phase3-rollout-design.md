# Phase 3 Rollout Design

**Date:** 2026-05-20
**Status:** Proposed design
**Scope:** Phase 3 rollout sequencing for `PycHermesAgent`
**Primary references:**
- `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
- `docs/architecture/Phase3A_Desktop_Integration_Plan_v0.3.0.md`
- `docs/architecture/Phase3B_Network_Search_Plan_v0.3.0.md`
- `docs/architecture/Phase3C_Multiformat_MRAG_Plan_v0.3.0.md`
- `docs/architecture/Phase3D_Skills_Rules_Runtime_Plan_v0.3.0.md`
- `docs/architecture/Phase3E_PPT_XLSX_Authoring_Plan_v0.3.0.md`
- `docs/architecture/Phase3F_Retrieval_MetaFramework_Strengthening_Plan_v0.3.0.md`
- `docs/architecture/Phase3G_Windows_Release_Hardening_Plan_v0.3.0.md`

## 1. Goal

Define how Phase 3 should actually be executed on top of the current repository state.

This design does not replace the existing Phase 3 roadmap documents. It turns them into an execution shape that fits the current codebase, reduces rework, and makes parallel delivery realistic.

## 2. Current Repository Reality

Phase 3 is not starting from a blank slate.

Already present in the repository:

- Electron desktop preview shell and real Python sidecar HTTP/SSE surfaces.
- `hermes_engine.AgentLoop` with tool support and formal-analysis integration.
- `MetaFramework.execute()` as the formal-analysis entry point.
- MRAG text, file, URL, and PDF ingestion foundations.
- Builtin skills, discovered `.opencode` skills metadata, and rules discovery.
- Artifact export foundations and Windows packaging probes.

Important gaps discovered during repository review:

- Desktop and sidecar contracts have drift in routes, SSE event names, and payload expectations.
- Citation and evidence models are too shallow for upcoming multi-format MRAG and network evidence work.
- PDF provenance is not preserved end to end strongly enough.
- The `/skills` surface is only partially normalized: the sidecar already returns `items` and `builtin`, but discovered entries and desktop consumers still disagree on stable entry shape.
- The current sidecar MRAG runtime still persists JSON manifests and chunk indexes even though SQLite/FTS5 artifacts and migration scaffolding also exist in the repository.
- Release-gate and desktop packaging configuration contain drift that should not wait until the end.

Because of those gaps, Phase 3 should not be executed as a simple document-order feature stream.

Repository-locked facts for `P0` execution:

- The canonical formal-analysis route is `/formal-analysis`; desktop code still contains drift toward `/meta/analyze`.
- The canonical stream route is `/agent/run/stream`; canonical assistant events are `assistant.delta`, `assistant.tool_call.delta`, `tool.result`, `done`, and `error`.
- The `/skills` route already returns an object shaped as `{"items": ..., "builtin": ...}`; `P0` only needs to normalize entry fields and desktop consumption.
- The currently active sidecar MRAG runtime is the JSON-backed `MRAGService` path under `mrag_core.persistence`; SQLite/FTS5 code exists but is not the active runtime backend yet.
- Release gates and deployment docs still refer to `npm run dist:linux`, while `desktop/package.json` currently exposes `pack`, `dist`, and `dist:win` only.

## 3. Recommended Rollout Strategy

Three rollout styles were considered:

1. Document-order execution: `3A -> 3B -> 3C -> 3D -> 3E -> 3F -> 3G`
2. Feature-first execution: prioritize user-visible capabilities before runtime stabilization
3. Foundation-first layered rollout

Recommended strategy: foundation-first layered rollout.

Reason:

- It matches the current code reality better than a pure roadmap-order push.
- It prevents repeated contract churn across desktop, sidecar, MRAG, skills, and release tooling.
- It allows multiple workstreams to move in parallel after a short stabilization phase.

## 4. Rollout Waves

Phase 3 should be executed as eight waves.

### P0. Shared Foundation Calibration

Purpose: remove cross-track drift before major new feature work starts.

Primary focus:

- desktop-sidecar route, formal-analysis, and SSE contract alignment
- citation and evidence schema alignment with PDF provenance preservation
- skill inventory payload normalization across builtin and discovered entries
- MRAG runtime backend and storage-path clarification
- packaging and release-gate configuration drift cleanup

Success criteria:

- desktop-sidecar contracts are consistent
- Phase 3 evidence schema is frozen at a practical first version
- skill inventory shape is consistent between sidecar and desktop
- current MRAG runtime truth is visible and no longer implied incorrectly by docs
- release checks and desktop packaging scripts stop disagreeing

### P1. Phase 3A Desktop Integration

Purpose: turn the desktop from a preview shell into a real sidecar-backed runtime shell.

Primary focus:

- sidecar attach/launch contract
- health and degraded-state UX
- real SSE chat runtime validation
- sidecar-managed services shown through desktop UI

Success criteria:

- desktop can attach to or launch the real sidecar reliably
- health failures are visible and actionable
- streaming chat works against the real sidecar

### P2. Phase 3C Core MRAG Foundation

Purpose: establish the multi-format MRAG backbone before broad format expansion.

Primary focus:

- parser registry refactor
- richer citation metadata
- migration and compatibility discipline
- PDF provenance preservation as the first end-to-end proof

Success criteria:

- parser dispatch is centralized
- richer citation metadata survives ingest to retrieval to UI
- compatibility and rebuild rules are explicit

### P3. Phase 3B Network Search

Purpose: add network evidence on top of the stabilized evidence model.

Primary focus:

- provider-neutral search abstraction
- `web_search` runtime tool
- sidecar evidence serialization
- desktop display of network evidence
- formal grounding through existing MetaFramework entry rules

Success criteria:

- network search is usable as a real tool
- internet evidence appears in the same user-facing evidence flow as local evidence
- failure modes are recoverable and explicit

### P4. Phase 3D Skills and Rules Runtime

Purpose: turn skills and rules into a true runtime extension system.

Primary focus:

- unified skill inventory across builtin, project, and user scopes
- runtime skill assembly
- deterministic rule precedence
- audit and provenance expansion
- user-requested skill authoring before habit-derived synthesis

Success criteria:

- skills and rules materially affect runtime behavior in a traceable way
- provenance is visible in sidecar and desktop surfaces
- extension management becomes reliable and inspectable

### P5. Phase 3F Retrieval and MetaFramework Strengthening

Purpose: strengthen how evidence is ranked, validated, and passed into formal analysis.

Primary focus:

- retrieval quality improvements
- benchmark expansion
- multi-source conflict handling
- chain and temporal validation
- structured evidence packaging into `MetaFramework.execute()`

Success criteria:

- formal outputs can explain their evidence basis clearly
- conflict and degraded evidence states are explicit
- retrieval quality improvements are benchmarked instead of assumed

### P6. Phase 3E PPT and XLSX Authoring

Purpose: add typed office-document output after runtime and evidence structures are stable.

Primary focus:

- typed artifact export interfaces
- PPTX/XLSX exporter MVPs
- template and styling baseline
- prompt-to-artifact flow
- desktop artifact visibility

Success criteria:

- basic office artifacts can be generated, listed, and opened
- artifact metadata remains versioned and separated from MRAG storage

### P7. Phase 3G Windows Release Hardening

Purpose: close the release path after product behavior stabilizes.

Primary focus:

- CI packaging coverage
- clean-machine install smoke
- updater validation
- signing preparation
- upgrade and downgrade safety
- release-gate expansion

Success criteria:

- packaging and startup are validated in real Windows conditions
- release gates reflect actual delivery requirements

## 5. Required Ordering

These dependencies should be treated as hard ordering constraints:

1. `P0 -> P1`
2. `P0 -> P2`
3. `P2 -> P3`
4. `P2 + P3 -> P5`
5. `P1 -> P7`

Rationale:

- Desktop integration should not be built on drifting contracts.
- Network evidence should not land before local evidence structures stabilize.
- Evidence-chain strengthening should happen after both local and network evidence paths are real.
- Release hardening should validate the real product shell, not the preview shell.

## 6. Parallel Workstreams

After `P0`, Phase 3 should be executed through three parallel lines.

### A. Runtime Shell Line

Flow: `P0 -> P1 -> P7`

Primary modules:

- `desktop/*`
- `src/pyc_hermes_agent/sidecar_api/*`
- `packaging/windows/*`
- `.github/workflows/*`

### B. Evidence and Grounding Line

Flow: `P0 -> P2 -> P3 -> P5`

Primary modules:

- `src/pyc_hermes_agent/mrag_core/*`
- `src/pyc_hermes_agent/contracts/*`
- `src/pyc_hermes_agent/meta_harness/*`
- `src/pyc_hermes_agent/hermes_engine/*`

### C. Extensions and Outputs Line

Flow: `P0 -> P4 -> P6`

Primary modules:

- `src/pyc_hermes_agent/llm_gateway/skills.py`
- `src/pyc_hermes_agent/llm_gateway/rules.py`
- `src/pyc_hermes_agent/hermes_engine/skills/*`
- `src/pyc_hermes_agent/artifact_engine/*`
- `desktop/src/components/skills/*`

## 7. Freeze Points

Five freeze points should be declared and protected by tests.

### F0. Desktop-Sidecar Protocol Freeze

Includes:

- canonical HTTP route names including `/formal-analysis` and `/agent/run/stream`
- SSE event names
- done and error semantics
- desktop-sidecar request and response shape expectations

### F1. Citation and Evidence Schema Freeze

Includes:

- citation fields
- chunk metadata fields
- minimal source anchor fields such as `source_type`, `page`, `section`, and `relevance`
- P0-first support for `text`, `file`, `url`, and `pdf`; richer sheet/slide/image anchors land later

### F2. Skill Inventory Freeze

Includes:

- stable entry fields such as `id`, `name`, `description`, `category`, `active`, and `source_kind`
- `/skills` response shape using `items` and `builtin`
- skill provenance and activation-visibility fields needed by sidecar and desktop
- not included in `P0`: runtime rule precedence and full rules assembly, which remain `P4` work

### F3. Runtime Truth And Packaging Command Freeze

Includes:

- sidecar-declared MRAG runtime backend truth
- runtime-path and packaging command names shared by `release_gates.py`, `desktop/package.json`, and deployment docs
- explicit distinction between current runtime backend and future storage convergence work

### F4. Artifact Request and Metadata Freeze

Includes:

- typed office export request shapes
- artifact metadata fields
- desktop artifact display expectations

## 8. Wave Milestones

### P0 Milestones

1. `P0-M1` desktop-sidecar protocol calibration
2. `P0-M2` citation and evidence schema calibration
3. `P0-M3` skills and rules runtime model calibration
4. `P0-M4` MRAG runtime storage path calibration
5. `P0-M5` packaging and release-gate drift calibration

### P1 Milestones

1. `P1-M1` sidecar startup contract
2. `P1-M2` health and degraded-state UX
3. `P1-M3` real SSE runtime validation
4. `P1-M4` sidecar runtime services in desktop UX

### P2 Milestones

1. `P2-M1` parser registry
2. `P2-M2` citation metadata upgrade
3. `P2-M3` compatibility and migration closure

### P3 Milestones

1. `P3-M1` search provider abstraction
2. `P3-M2` runtime tool integration
3. `P3-M3` sidecar and desktop evidence integration
4. `P3-M4` formal grounding bridge

### P4 Milestones

1. `P4-M1` unified skill inventory
2. `P4-M2` runtime assembly
3. `P4-M3` rule precedence
4. `P4-M4` audit and provenance
5. `P4-M5` authoring and proposal flow

### P5 Milestones

1. `P5-M1` retrieval strengthening baseline
2. `P5-M2` evidence convergence and conflict handling
3. `P5-M3` chain validation
4. `P5-M4` formal evidence packaging

### P6 Milestones

1. `P6a` exporter core
2. `P6b` product-flow integration

### P7 Milestones

1. `P7-M1` CI packaging coverage
2. `P7-M2` clean-machine install smoke
3. `P7-M3` updater and signing preparation
4. `P7-M4` release-gate expansion

## 9. First Execution Round

The first execution round should focus only on `P0`, while opening the path to `P1` and `P2`.

Recommended first tasks:

1. Align desktop-sidecar API and SSE contracts.
2. Fix the `/skills` entry-normalization mismatch between sidecar and desktop stores while keeping the existing `items` and `builtin` envelope.
3. Fix formal-analysis route drift.
4. Preserve PDF citation provenance end to end.
5. Freeze the first practical Phase 3 citation and evidence schema.
6. Clarify that the current sidecar MRAG runtime remains JSON-backed while SQLite/FTS5 artifacts stay future-facing.
7. Fix obvious release-gate and packaging-script drift.
8. Add regression coverage for the items above.

These tasks are intentionally small enough to stabilize the shared surface before Track A, Track B, and Track C begin wider construction.

## 10. Verification Strategy

Phase 3 should use a contract-first verification strategy.

### Contract Layer

Primary targets:

- `tests/contract/test_sidecar_http.py`
- `tests/contract/test_sidecar_api.py`
- `tests/contract/test_sidecar_client.py`
- `tests/contract/test_hermes_agent_loop.py`
- `tests/contract/test_skills_system.py`
- `tests/contract/test_mrag_core.py`

Purpose:

- lock interfaces before expanding functionality

### Module Layer

Examples:

- desktop runtime behavior for `P1`
- parser and citation fidelity for `P2`
- search provider and tool handling for `P3`
- skill assembly and audit for `P4`
- retrieval benchmarks and evidence-chain checks for `P5`
- exporter openability and metadata checks for `P6`
- packaging and upgrade-path checks for `P7`

### Integration Smoke Layer

Keep these as recurring checks:

- `npx electron-vite build`
- real `/health` smoke
- real `/agent/run/stream` smoke
- packaged desktop smoke where applicable

### Gate Layer

- run `scripts/release_gates.py` before declaring meaningful completion
- update `docs/architecture/Compatibility_Matrix.md` when Phase 3 contracts change

## 11. Exit Interpretation

For execution management, the following internal interpretation is recommended:

- Phase 3 primary delivery scope: `P0` through `P6`
- Phase 3 to Phase 4 release-closure track: `P7`

This keeps the internal delivery model aligned with the roadmap language while acknowledging that Windows release-grade hardening is a closure track rather than the first thing to build.

## 12. Key Boundary Rules During Execution

The rollout must preserve these boundaries:

- Formal analysis continues to enter through `MetaFramework.execute()`.
- Provider-specific objects remain inside `llm_gateway`.
- `mrag_core` owns ingestion, indexing, retrieval, and evidence packaging only.
- Office authoring remains inside `artifact_engine`, not `mrag_core`.
- Desktop supervises sidecar lifecycle but does not bypass sidecar-owned runtime domains.
- Install directories remain read-only.
- Skills remain explicit activation only until a later permissions model is approved.

## 13. Immediate Recommendation

Start Phase 3 with a narrow stabilization sprint scoped to `P0` only.

Do not begin by implementing network search, office exporters, or habit-derived skills.

The correct first move is to reduce contract drift, freeze shared schemas, and make the platform ready for parallel track execution.
