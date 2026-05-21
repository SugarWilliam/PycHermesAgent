# Hermes Mixed Integration Mapping v0.2.0

**Status:** Accepted integration guardrail

## 1. Principle

PycHermesAgent uses a mixed integration strategy with upstream `upstream/hermes-agent`. The product must not blindly embed the upstream runtime. Product orchestration is rebuilt and owned in `hermes_engine`; upstream Hermes is used through read-only bridge snapshots, selected conceptual reuse, and future controlled adapters.

## 2. Integration Modes

| Capability Area | Mode | Product Owner | Rule |
|-----------------|------|---------------|------|
| Agent orchestration | Rebuild | `hermes_engine` | Do not embed upstream `run_agent.py` as product runtime |
| Session concepts | Deep bridge over time | `hermes_engine` | Preserve product session contracts |
| Memory concepts | Deep bridge over time | `hermes_engine` + `mrag_core` | Do not mix chat memory and MRAG indexes |
| Skills metadata | Compatibility | `llm_gateway` and `hermes_engine` | Discover first, explicit runtime binding later |
| Provider execution | Product implementation | `llm_gateway` | Provider objects must not leak |
| Tools | Product registry | `hermes_engine` | Tool execution must be auditable |
| Upstream diagnostics | Read-only snapshots | `HermesFacade` | No product state mutation in upstream checkout |
| Desktop UI | Product implementation | desktop shell | Do not depend on upstream UI as release shell |

## 3. Current Bridge State

`HermesFacade` may inspect repository presence, worktree state, sessions, memory, skills, and tools through static discovery and controlled probes. These snapshots are diagnostic and compatibility surfaces. They are not the product runtime.

## 4. Production Path

The production path is:

1. Keep read-only bridge health stable.
2. Stabilize product-owned AgentLoop.
3. Add explicit skill activation.
4. Add safer memory and retrieval integration.
5. Only then consider deeper adapters for selected upstream concepts.

## 5. Forbidden Shortcuts

- Do not import upstream provider internals into `meta_harness`.
- Do not run upstream CLI as the main product loop.
- Do not write product runtime state into `upstream/hermes-agent`.
- Do not make bridge snapshots authoritative for release health without sidecar contract tests.
