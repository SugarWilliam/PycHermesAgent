# PycHermesAgent Phase 0 Blueprint v0.2.0

**Status:** Historical baseline, absorbed into production governance

Phase 0 established the governance, architecture boundaries, package skeleton, core contracts, compatibility scope, and initial contract tests. It remains important as a historical baseline, but future work is governed by `docs/Project_Development_and_Release_Governance.md` and the active Phase 1 roadmap.

## Phase 0 Deliverables

- `AGENTS.md` project boundaries.
- `opencode.jsonc` compatibility configuration.
- Package skeleton under `src/pyc_hermes_agent`.
- Contract tests under `tests/contract`.
- Architecture, design, feature, deployment, and constraints documents.
- Initial OpenCode skill compatibility material.

## Continuing Constraints

The following Phase 0 constraints remain active:

- Formal analysis through `MetaFramework.execute()`.
- Provider isolation in `llm_gateway`.
- MRAG storage separation.
- Install-directory immutability.
- Contract tests before integration and UI tests.

## Superseded Planning Role

This document no longer defines the active roadmap. Use `Phase1_Roadmap_v0.2.0.md` and `Execution_Blueprint_v0.2.0.md` for current implementation order.
