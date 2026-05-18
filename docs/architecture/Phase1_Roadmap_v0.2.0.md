# PycHermesAgent Phase 1 Roadmap v0.2.0

**Status:** Active roadmap for engineering preview hardening
**Governance:** `docs/Project_Development_and_Release_Governance.md`

## 1. Phase 1 Goal

Phase 1 converts the current working MVP into a hardened local-first engineering preview with stable sidecar contracts, protected local persistence, explicit skill lifecycle, and measurable MetaHarness value. Phase 1 does not claim production readiness or desktop completeness.

## 2. Current Completed Baseline

Completed and contract-tested surfaces include:

- Sidecar health, config, provider/model/rule/skill discovery; `GET /runtime-paths`; structured HTTP error domains; `GET /favicon.ico` (204) for browser noise.
- HTTP JSON and SSE transport with **`X-Pyc-Request-Id`** (accept or generate) echoed on responses and merged into error details where applicable.
- Direct LLM runtime paths for configured OpenAI-compatible, OpenRouter, and GitHub Copilot style providers.
- Product-owned `AgentLoop` with tool calls, session persistence, bounded memory injection, planning, retry budgeting, and event streaming.
- `formal_analysis` tool integration through `MetaFramework.execute()` with optional **`target_sr_grade`** and **`meta_routing`** (keyword overlays, `data_shape_bonus`, declarative `data_shape_rules`, `pin_method`, tunable scores).
- **MetaHarness:** `MethodRoutingPolicy` + `MethodSelector` (language + data-shape + dependency penalty + `allowed_methods` filter); **`SrGradingPolicy`** (CE/SR dimensions kept separate; degraded/overclaim/execution failure map to SR bands); dependency snapshot; benchmark smoke + **value_proof** benchmark (contract-tested).
- Text MRAG knowledge bases with lexical retrieval, **storage owner/lock** (`MRAGStorageOwner`), manifest/index version guards, file/URL ingest, chunk index rebuild sidecar surface.
- Local asset and artifact foundations; sidecar inventory routes.
- **Release gates:** `scripts/release_gates.py` runs **`pytest tests`**, optional **ruff** (`--with-ruff` / `RELEASE_GATES_RUFF=1`) and opt-in **mypy** (`--with-mypy`), CI-aware **`git diff --check`**, secret heuristics; optional `--export-meta-benchmarks`, `--write-preview-release-notes`.
- **CI:** `.github/workflows/ci.yml` — **uv** + **`uv.lock`**, Python **3.11/3.12** matrix, packaging probe, gates with `GITHUB_EVENT_NAME` / `GITHUB_BASE_REF`.
- **Desktop (preview):** Electron shell — health + runtime paths, URL resolution (env → `sidecar_url.txt` → default), probe retry (linear backoff), menus; optional sidecar auto-spawn via **`PYC_HERMES_SIDECAR_CMD`** (defaults to **no shell**; see `desktop/README.md`).

## 3. Phase 1 Workstreams (status)

| Workstream | Status | Exit / notes |
|------------|--------|----------------|
| A: MRAG ownership | **Done (MVP)** | `mrag_core/ownership.py`, contract tests; multi-process lock errors structured |
| B: Trace propagation | **Done (MVP)** | Request ID on HTTP/SSE/errors; AgentLoop `trace_id` separate |
| C: Skill lifecycle | **Partial** | Explicit activation + metadata; script execution still disabled by policy |
| D: MetaHarness value | **Advanced** | Routing policy + SR grading + benchmarks contract-tested; pluggable policies via ctor |
| E: MRAG productization | **Partial** | Lexical retrieval + ingest + versioning + rebuild; vectors/semantic later |
| F: Release gates | **Done (preview line)** | Gates + CI; **ruff** via `RELEASE_GATES_RUFF=1` / `--with-ruff`; **mypy** opt-in (`--with-mypy`) |

## 4. Workstream A: MRAG Ownership

Implementation must protect `mrag_core` persistence from uncoordinated multi-process writes. The accepted MVP is a single-process owner or lock guardrail. It is not necessary to implement a production database before this guardrail exists.

## 5. Workstream B: Trace Propagation

Every externally visible sidecar operation must become diagnosable. Request IDs must appear in errors, logs, and streaming events. Agent loop trace IDs remain separate and must be correlated rather than replaced.

## 6. Workstream C: Skill Lifecycle

Skill behavior must evolve in this order:

1. Discovery and metadata parsing.
2. Explicit activation request.
3. Controlled context binding.
4. Auditable activation metadata.
5. Permission-gated script execution in a later phase.

No skill script execution is allowed in Phase 1 without an explicit permission model. **See `docs/design/ADR_Skill_Runtime_Permissions_Phase1_v0.2.0.md`** for Phase 1 vs deferred scope.

## 7. Workstream D: MetaHarness Value

The evaluation report identified the most important risk: the methodology layer can become hollow if routing and judging remain only templates. Phase 1 must begin proving value through:

- realistic capability availability checks,
- method precondition checks,
- configurable **`MethodRoutingPolicy`** and per-request **`meta_routing`** (without bypassing **`MetaFramework.execute()`**),
- benchmark cases,
- degraded-state correctness,
- evidence-grade and **SR-grade** correctness (separate dimensions).

## 8. Workstream E: MRAG Productization

MRAG remains local-first and evidence-grounded. Phase 1 may expose file and URL text ingestion and index version checks. Semantic embedding, reranking, and multimodal parsing remain later work unless the storage guardrail and migration rules are complete.

## 9. Workstream F: Release Gates

A preview release candidate may be tagged only when:

- `./.venv/bin/python -m pytest tests -q` (or `uv run pytest tests -q`) passes — same scope as `scripts/release_gates.py`,
- `scripts/release_gates.py` passes (whitespace + secret heuristics in repo with `.git`),
- docs and **compatibility matrix** are updated for format/API changes,
- no secrets or runtime assets are staged,
- release notes stub or draft exists (`scripts/release_gates.py --write-preview-release-notes`; see `docs/releases/README.md`).

## 10. Phase 1 Exit Criteria

Phase 1 **core exit** (engineering-preview hardening) is **largely satisfied** for items 1–2, 4–5 above; item 3 (skill lifecycle) remains **partial** until permission-gated execution is specified.

Formal **Phase 1 exit** declaration should still wait until:

1. Skill workstream exit gate is explicit (or consciously deferred with ADR).
2. Maintainers record current status in governance + compatibility matrix for any new contract fields (e.g. `MetaAnalysisRequest.meta_routing`).

The repository must still state clearly whether it is engineering preview, release candidate, or production release.
