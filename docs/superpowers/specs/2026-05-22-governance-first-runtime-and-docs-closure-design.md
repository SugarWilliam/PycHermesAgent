# Governance-First Runtime Fix And Docs Closure Design

**Date:** 2026-05-22
**Status:** Approved design
**Scope:** Runtime verification unblock plus governance-first docs closure for the current `main` baseline
**Primary references:**
- `AGENTS.md`
- `docs/Project_Development_and_Release_Governance.md`
- `docs/architecture/Compatibility_Matrix.md`
- `docs/deployment/Production_Release_Gates.md`
- `docs/Documentation_Tracking.md`

## 1. Goal

Restore a fully verifiable `main` baseline in the root workspace, then close documentation drift without collapsing governance and design documents into code snapshots.

This work is intentionally split into two ordered parts:

1. unblock verification with the smallest root-cause runtime fix
2. close documentation drift using a governance-first review order

## 2. Non-Negotiable Principle

Docs are not a passive mirror of code.

- Governance, architecture, and constraints documents remain the product contract.
- Compatibility and release-gate documents remain the current operational baseline.
- README, release notes, and execution notes describe status, progress, and known gaps.
- Historical specs and plans remain historical design artifacts; they may receive status or drift notes, but they should not be rewritten into implementation transcripts.

## 3. Document Authority Order

### 3.1 Tier 1: governance and blueprint authority

These documents define intended direction and boundaries and must not be rewritten just to match accidental implementation state:

- `AGENTS.md`
- `docs/Project_Development_and_Release_Governance.md`
- `docs/architecture/*.md`
- `docs/constraints/*.md`

### 3.2 Tier 2: current baseline and contract truth

These documents describe the repository's current contract and operational state and should be corrected when they drift from validated implementation or governing documents:

- `docs/architecture/Compatibility_Matrix.md`
- `docs/deployment/Production_Release_Gates.md`
- `docs/Documentation_Tracking.md`

### 3.3 Tier 3: status, release, and execution artifacts

These documents communicate progress and current state. They may be updated to reflect verified implementation, but only within their intended role:

- `README.md`
- `docs/releases/*.md`
- `docs/superpowers/specs/*.md`
- `docs/superpowers/plans/*.md`

Rules:

- current-status documents should be corrected when facts drift
- historical release documents should keep their historical identity but may receive clear scope/status wording if they currently present themselves as the active truth
- historical specs and plans should receive status/drift notes rather than full implementation rewrites

## 4. Runtime Root-Cause Fix

The current verification blocker is not a generic Windows filesystem problem.

Validated root cause:

- `tests/contract/test_hermes_agent_loop.py::test_agent_loop_binds_session_context_for_sync_llm_and_tool_dispatch` fails only in broader-suite execution, not in isolation
- failure writes to `%LOCALAPPDATA%/PycHermesAgent/hermes_engine/sessions/...`
- the failing tests instantiate `AgentLoop(root=tmp_path, ...)` without explicitly passing `storage_root`
- `AgentLoop` currently uses `root` for prompt/runtime context but does not use it to default session persistence
- this leaks test session persistence into the shared runtime location, creating cross-test interference and Windows file-replacement conflicts

Required fix:

- when `session_store` is not explicitly provided and `storage_root` is not explicitly provided, `AgentLoop` must default `AgentSessionStore` to the same sandbox root as `root`
- explicit `session_store` still wins over everything
- explicit `storage_root` still wins over inferred storage from `root`

This is a runtime isolation fix, not a packaging rule change.

## 5. Docs Closure Strategy

After verification is green, docs closure follows this matrix.

### 5.1 If blueprint is correct and code is incomplete

Do not weaken the blueprint.

Instead:

- record the gap in status-facing docs
- keep the intended target in the governing document

### 5.2 If blueprint is correct and code is complete but status docs are stale

Update status-facing docs:

- `README.md`
- `docs/releases/README.md`
- any active baseline/compatibility note that communicates current truth

### 5.3 If historical spec/plan content no longer matches the delivered implementation

Do not rewrite the full document as if it were authored after implementation.

Allowed closure:

- update the top-level `Status:` line
- add a concise note describing where implementation diverged or what has since been closed

## 6. Targeted Docs To Review

The closure pass should specifically evaluate:

- `README.md`
- `docs/architecture/Compatibility_Matrix.md`
- `docs/releases/README.md`
- `docs/releases/preview_draft.md`
- `docs/releases/v0.3.0.md`
- `docs/superpowers/specs/2026-05-20-phase3-rollout-design.md`
- `docs/superpowers/plans/2026-05-21-phase3a-a1-sidecar-startup.md`
- `docs/Documentation_Tracking.md`

## 7. Verification Requirements

The work is only complete when all of the following are re-run successfully from the root workspace:

- `python -m pytest tests/contract/test_hermes_agent_loop.py -q`
- `python -m pytest tests/contract tests/integration -q`
- `python scripts/release_gates.py`
- portable Node: `node --test desktop/electron/sidecarRuntime.test.js`

## 8. Expected Outcome

At the end of this work:

- root `main` is again a passing, verifiable development baseline
- governance and architecture docs remain the authority
- baseline and status docs stop contradicting validated repository behavior
- historical design documents remain historical, but their current relevance and drift are no longer ambiguous
