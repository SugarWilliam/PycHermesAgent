# PycHermesAgent Phase 0 Blueprint

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Ready for Implementation |

## Phase 0 Goals

Phase 0 freezes the parts of the system that should not drift during implementation:

1. Governance documents
2. Project rules and skills
3. Package skeleton
4. Cross-layer contracts
5. Packaging and storage boundaries
6. Compatibility scope

## Deliverables

1. Architecture documents in `docs/architecture/`
2. Constraint documents in `docs/constraints/`
3. `AGENTS.md`
4. `opencode.jsonc`
5. `.opencode/skills/*/SKILL.md`
6. `pyproject.toml`
7. `src/pyc_hermes_agent/` package skeleton
8. `tests/contract/` skeleton

## Success Criteria

- The project has a stable ruleset.
- The project has a stable `opencode` compatibility entry.
- The project has a stable package structure.
- The first code iteration no longer depends on ad hoc flat scripts as the product runtime.

## Explicit Non-Goals

- Full Electron desktop implementation
- Full MRAG pipeline
- Full Hermes runtime integration
- Full provider login flows
- Full migration of all legacy adapters

## Phase 1 Entry Condition

Phase 1 starts only after all governance files, contracts, and skeleton modules are committed to the repository and validated with smoke tests.
