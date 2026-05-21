# Governance-First Runtime And Docs Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a fully passing root `main` baseline, then close documentation drift using governance and blueprint documents as the authority.

**Architecture:** This plan first fixes the verified `AgentLoop` session-storage isolation bug with TDD, because a non-verifiable baseline cannot support honest docs closure. After verification is green, it updates only the documents whose role is to describe current contract, progress, and drift, while preserving governance and historical design documents in their proper roles.

**Tech Stack:** Python 3.12, pytest, Electron/Node built-in test runner, Markdown docs

---

## File Structure And Responsibilities

- `tests/contract/test_hermes_agent_loop.py`
  Regression coverage for default `AgentLoop` session-storage sandbox behavior.
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
  Runtime fix for default session-store root inference.
- `README.md`
  Current project status and contributor-facing entrypoint.
- `docs/architecture/Compatibility_Matrix.md`
  Current contract and baseline truth.
- `docs/releases/README.md`
  Release-note generation workflow and authority references.
- `docs/releases/v0.3.0.md`
  Historical release notes that currently overstate active runtime truth.
- `docs/releases/preview_draft.md`
  Historical/draft preview notes that currently overstate active runtime truth.
- `docs/superpowers/specs/2026-05-20-phase3-rollout-design.md`
  Historical design doc that needs explicit status/drift framing.
- `docs/superpowers/plans/2026-05-21-phase3a-a1-sidecar-startup.md`
  Historical implementation plan that needs concise drift correction.
- `docs/Documentation_Tracking.md`
  Docs inventory updated for the new spec and plan.

### Task 1: Fix AgentLoop Session Storage Isolation

**Files:**
- Modify: `tests/contract/test_hermes_agent_loop.py`
- Modify: `src/pyc_hermes_agent/hermes_engine/agent_loop.py`

- [ ] **Step 1: Add the failing regression test**

Use a focused test that proves `AgentLoop(root=tmp_path, ...)` defaults session persistence into the sandbox when `storage_root` is omitted.

- [ ] **Step 2: Run the regression test and verify it fails for the right reason**

Run: `python -m pytest tests/contract/test_hermes_agent_loop.py::test_agent_loop_defaults_session_storage_to_root_sandbox -q`
Expected: FAIL because the saved session is not found in `tmp_path/.pyc_hermes_agent_runtime/...`

- [ ] **Step 3: Implement the minimal fix in `AgentLoop.__init__`**

Keep constructor precedence:

1. explicit `session_store`
2. explicit `storage_root`
3. inferred `root`

- [ ] **Step 4: Re-run the new regression and the previously failing test**

Run:
- `python -m pytest tests/contract/test_hermes_agent_loop.py::test_agent_loop_defaults_session_storage_to_root_sandbox -q`
- `python -m pytest tests/contract/test_hermes_agent_loop.py::test_agent_loop_binds_session_context_for_sync_llm_and_tool_dispatch -q`

Expected: both PASS

- [ ] **Step 5: Run the full Hermes agent-loop contract file**

Run: `python -m pytest tests/contract/test_hermes_agent_loop.py -q`
Expected: PASS

### Task 2: Re-Verify The Root Main Baseline

**Files:**
- Modify: none

- [ ] **Step 1: Run contract and integration suites**

Run: `python -m pytest tests/contract tests/integration -q`
Expected: PASS with the existing single skip only

- [ ] **Step 2: Run release gates**

Run: `python scripts/release_gates.py`
Expected: `release_gates: OK`

- [ ] **Step 3: Run the desktop targeted test with portable Node**

Run: `C:\Users\ADMINI~1\AppData\Local\Temp\opencode\node-portable\node-v22.22.3-win-x64\node.exe --test desktop/electron/sidecarRuntime.test.js`
Expected: PASS

### Task 3: Close Current-State Doc Drift

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/Compatibility_Matrix.md`
- Modify: `docs/releases/README.md`
- Modify: `docs/Documentation_Tracking.md`

- [ ] **Step 1: Update `README.md` to reflect the current repository baseline honestly**

Keep it as a current-status entrypoint, not a release note or roadmap clone.

- [ ] **Step 2: Update `Compatibility_Matrix.md` only where current contract truth is stale or ambiguous**

Clarify active truth for current sidecar/runtime surfaces without weakening higher-level architecture intent.

- [ ] **Step 3: Update `docs/releases/README.md` to reference current governance + current execution spine**

Remove outdated roadmap anchoring where it now points to a closed historical execution stream.

- [ ] **Step 4: Add the new spec/plan to `docs/Documentation_Tracking.md`**

Update both summary tables and manifest list.

### Task 4: Add Minimal Drift Notes To Historical Docs

**Files:**
- Modify: `docs/releases/v0.3.0.md`
- Modify: `docs/releases/preview_draft.md`
- Modify: `docs/superpowers/specs/2026-05-20-phase3-rollout-design.md`
- Modify: `docs/superpowers/plans/2026-05-21-phase3a-a1-sidecar-startup.md`

- [ ] **Step 1: Preserve historical identity of the two release-note files**

Do not rewrite them as current-source-of-truth documents. Add concise wording so readers do not mistake them for the active baseline when newer current-truth docs disagree.

- [ ] **Step 2: Add concise status/drift framing to the historical rollout spec**

Keep its design content, but make clear that some repository-locked facts documented there have since been closed.

- [ ] **Step 3: Add concise status/drift framing to the A1 plan where the finalized IPC surface differs**

Do not rewrite the plan body as an implementation report.

### Task 5: Final Verification And Summary

**Files:**
- Modify: none

- [ ] **Step 1: Run `git status --short --branch --ignored`**

Capture the final working tree state and confirm no unintended files were introduced.

- [ ] **Step 2: Re-run the full required verification set after docs updates**

Run:
- `python -m pytest tests/contract tests/integration -q`
- `python scripts/release_gates.py`
- `C:\Users\ADMINI~1\AppData\Local\Temp\opencode\node-portable\node-v22.22.3-win-x64\node.exe --test desktop/electron/sidecarRuntime.test.js`

Expected: all PASS

- [ ] **Step 3: Summarize remaining risks without overstating completion**

Call out any still-open architecture or product gaps that remain intentionally future work.
