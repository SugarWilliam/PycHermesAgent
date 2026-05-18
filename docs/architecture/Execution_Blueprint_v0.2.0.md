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

**Engineering-preview baseline (contract-tested today):** MRAG storage ownership MVP; HTTP **`X-Pyc-Request-Id`** correlation; explicit skill activation surfaces; **MetaHarness** dependency-aware routing with **`MethodRoutingPolicy`**, data-shape scoring, **`meta_routing`** overlays (**`data_shape_bonus`**, **`data_shape_rules`**, **`pin_method`**), **`SrGradingPolicy`**; benchmark smoke + value_proof; MRAG ingest, manifest/index guards, rebuild; asset/artifact inventory; **`scripts/release_gates.py`** (pytest **`tests`**, CI-aware whitespace, secret heuristics, optional benchmark export and preview release notes); **GitHub CI** via **uv** + **`uv.lock`**; preview **desktop** shell (health, runtime paths, URL file, spawn hardening — see `desktop/README.md`).

**Next waves toward production:**

| Order | Workstream | Goal | Primary Docs |
|-------|------------|------|--------------|
| 1 | Skill lifecycle | Permission model and auditable execution path (sandbox later) | opencode constraints, governance |
| 2 | MRAG semantics | Embedding/rerank per index strategy ADR; keep lexical baseline | `docs/design/MRAG_Index_Strategy_Decision_v0.2.0.md` |
| 3 | Desktop packaging | Installer, signing, updater, CSP/sandbox | `docs/constraints/windows-packaging.md` |
| 4 | Release hardening | **Ruff** in CI/gates; **mypy** opt-in until clean; dependency audit optional | governance, compatibility matrix |
| 5 | Observability | Structured logs/metrics beyond health and runtime-paths | deployment guide |

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
- Method selection uses preconditions, language and data-shape scoring, and dependency penalty; optional **`meta_routing`** and **`allowed_methods`** constrain or pin routes without bypassing **`MetaFramework.execute()`**.
- **SR** outputs are computed by **`SrGradingPolicy`** (separate from CE **`evidence_grade`**); **`target_sr_grade`** may override when valid.
- Benchmark cases exist for causal overclaim, graph routing, dependency visibility, and degraded behavior; **value_proof** benchmark compares guided vs baseline stub (contract-tested).
- Benchmark results are documented before release claims.

### Slice 1E: MRAG Retrieval Productization

Acceptance:

- File and URL text ingestion are exposed as stable local sidecar contracts.
- Index format versions are checked.
- Retrieval results preserve citations.
- JSON vs SQLite/FTS5/vector decision is recorded in `docs/design/MRAG_Index_Strategy_Decision_v0.2.0.md`.

### Slice 2A: Asset and Artifact Inventory (Sidecar)

Contract surfaces:

- `GET /assets` lists installed assets discovered under the runtime models directory.
- `GET /artifacts` lists all artifacts; `GET /artifacts/task/{task_id}` scopes to one task.

Acceptance:

- Responses are JSON objects with an `items` array and stable field names.
- `SidecarClient` covers local and HTTP modes.
- Contract suite passes; `sidecar_api_version` reflects the contract bump.

## 5. Release Gates

Cursor may push, tag, or prepare release output only after these gates pass:

1. **`scripts/release_gates.py`** succeeds (includes **`pytest tests`**, optional **`ruff`** when `RELEASE_GATES_RUFF=1` or `--with-ruff`; optional **`mypy`** when `--with-mypy` / `RELEASE_GATES_MYPY=1`), tracked-file secret heuristics, **`git diff --check`** per environment (see script docstring).
2. Optional gate steps when cutting preview artifacts: **`--export-meta-benchmarks`**, **`--write-preview-release-notes`** (see script `--help`).
3. **CI** job **contract-tests** passes on **`main`/`master`** (Python 3.11 + 3.12, packaging probe).
4. Working tree is classified and intentional; no secrets or runtime assets staged.
5. `AGENTS.md` boundaries still hold; compatibility matrix and human-edited release notes updated when contracts change.
6. Tag name matches policy; no force push to protected branches, no skipped hooks unless explicitly approved.

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
