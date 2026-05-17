# PycHermesAgent Execution Blueprint v0.2.0

**Status:** Production execution blueprint
**Top-level governance:** `docs/Project_Development_and_Release_Governance.md`

## 1. Mission

This blueprint turns PycHermesAgent from an internal engineering preview into a production-grade, release-grade local-first agent platform. It is written for Cursor and future agentic workers that must independently implement, verify, document, commit, push, tag, and prepare releases under explicit gates.

## 2. Product Success Criteria

A production release must satisfy all of the following:

- The user can install and run the desktop product without writing mutable runtime data into the install directory.
- The sidecar starts, reports health, handles degraded state, and exposes stable local contracts.
- Agent sessions, skill/rule metadata, knowledge bases, artifacts, and relevant configuration survive restart.
- LLM execution remains fully isolated in `llm_gateway`.
- Formal analysis remains fully isolated behind `MetaFramework.execute()`.
- MRAG retrieval returns grounded citations and never claims CE/SR authority.
- Release artifacts are versioned, checksummed, and documented.
- All release gates pass before push/tag/release automation.

## 3. Immediate Execution Priorities

| Order | Workstream | Goal | Primary Docs |
|-------|------------|------|--------------|
| 1 | MRAG ownership | Protect JSON persistence with single-process or lock guardrails | `mrag-evidence-boundaries.md`, detailed design |
| 2 | Trace propagation | Correlate sidecar, AgentLoop, LLM, MRAG, and errors | detailed design, deployment guide |
| 3 | Skill lifecycle | Move from metadata discovery to explicit runtime binding | opencode constraints, detailed design |
| 4 | MetaHarness value proof | Prove routing, dependency status, and reliability improvement | evaluation report, detailed design |
| 5 | MRAG productization | Add file/url ingest, migration rules, retrieval evolution | feature details, compatibility matrix |
| 6 | Asset/artifact sidecar | Expose local asset and artifact foundations through contracts | deployment guide |
| 7 | Desktop shell | Add Electron lifecycle after sidecar contracts are stable | deployment guide |
| 8 | Release hardening | Automate checks, versioning, release notes, tag rules | governance, compatibility matrix |

## 4. Implementation Slices

### Slice 1A: MRAG Storage Ownership

Files expected to change during implementation:

- `src/pyc_hermes_agent/mrag_core/ownership.py`
- `src/pyc_hermes_agent/mrag_core/service.py`
- `src/pyc_hermes_agent/sidecar_api/service.py`
- `tests/contract/test_mrag_core.py`
- `tests/contract/test_sidecar_api.py`
- `tests/contract/test_sidecar_http.py`

Acceptance:

- Same process can reuse a storage root safely.
- A second process or incompatible owner receives a structured lock error.
- Lock release and restart behavior are tested.
- Contract suite passes.

### Slice 1B: Request and Trace Propagation

Acceptance:

- HTTP requests accept or generate a request ID.
- JSON errors and SSE events include request correlation.
- AgentLoop event `trace_id` and sequence remain stable.
- Logs can be joined with request ID.

### Slice 1C: Skill Runtime Lifecycle MVP

Acceptance:

- Skills can be discovered and explicitly activated.
- Activated skill context is injected only when requested.
- Script execution is disabled by default.
- Sidecar exposes activation metadata.

### Slice 1D: MetaHarness Reliability Proof

Acceptance:

- Capability availability reflects actual dependency and bridge state.
- Method selection uses method preconditions, not only keywords.
- Benchmark cases exist for causal overclaim, risk detection, and degraded-state behavior.
- Benchmark results are documented before release claims.

### Slice 1E: MRAG Retrieval Productization

Acceptance:

- File and URL text ingestion are exposed as stable local sidecar contracts.
- Index format versions are checked.
- Retrieval results preserve citations.
- JSON vs SQLite/FTS5/vector decision is recorded.

## 5. Release Gates

Cursor may push, tag, or prepare release output only after these gates pass:

1. Contract tests pass.
2. Scope-specific tests pass.
3. Runtime smoke test passes for sidecar health.
4. Working tree is classified and intentional.
5. No secrets or runtime assets are staged.
6. `AGENTS.md` boundaries still hold.
7. Compatibility matrix and release notes are updated.
8. Tag name is valid.
9. No force push, skipped hooks, or destructive git command is required.

## 6. Release Tag Policy

- Engineering preview tags use `v0.2.x-preview.N`.
- Release candidates use `v0.2.x-rc.N`.
- Production releases use `vX.Y.Z` only after all production release gates pass.
- Any storage format change must update the compatibility matrix before tag creation.

## 7. Failure Handling

If a gate fails, Cursor must stop and report:

- failing command or check,
- affected files,
- suspected root cause,
- safest next action,
- whether release automation is blocked.

Cursor must not push, tag, or release when verification is incomplete.
