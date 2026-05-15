# PycHermesAgent Architecture

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Active Architecture Baseline |

## Purpose

`PycHermesAgent` is a Windows desktop agent platform built around five clearly separated layers:

1. `hermes_engine`
2. `meta_harness`
3. `llm_gateway`
4. `mrag_core`
5. `desktop shell`

The goal is to preserve Hermes learning and memory strengths while adding a stable methodology harness that compensates for weak LLM logic, weak modeling discipline, and weak reasonableness checking.

## Layered Architecture

```text
Electron Desktop
├─ Main Process
├─ Renderer
└─ Typed IPC

Python Sidecar
├─ hermes_engine
├─ meta_harness
├─ llm_gateway
├─ mrag_core
├─ artifact_engine
└─ asset_manager

Local Storage
├─ config
├─ logs
├─ cache
├─ indexes
├─ models
├─ sessions
└─ artifacts
```

## Hard Boundaries

- Formal analysis must go through `MetaFramework.execute()`.
- `meta_harness` must not depend on provider auth, renderer state, or vector-store internals.
- `hermes_engine` must not implement methodology grading.
- `llm_gateway` must not leak provider-native objects upward.
- `mrag_core` must not absorb unrelated runtime caches.
- The install directory must remain read-only.

## Execution Strategy

1. Freeze governance and contracts.
2. Build `meta_harness` as a minimum viable base.
3. Add `opencode`-style compatibility for LLM configuration and discovery.
4. Add Hermes integration seams.
5. Add local-first MRAG.
6. Build the desktop shell after sidecar contracts are stable.

## Compatibility Strategy

The project intentionally supports the following `opencode` user-facing artifacts:

- `opencode.json`
- `opencode.jsonc`
- `AGENTS.md`
- `.opencode/skills/*/SKILL.md`

The project does not aim to embed the full `opencode` runtime.

## Sidecar Health Contract

- Product consumers must treat top-level `get_health()["status_label"]` as the first readiness signal.
- Nested `get_health()["hermes"]` fields are diagnostic detail and must not be used to re-derive initial readiness in clients.
- The minimal Python client entry point is `pyc_hermes_agent.SidecarClient`.
- If top-level `status_label` is missing, the client collapses to `degraded` when top-level `degraded` is `true`; otherwise it collapses to `unavailable`.

```python
from pyc_hermes_agent import SidecarClient

status = SidecarClient().get_health_status()
print(status.status_label)
```

## Related Documents

- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
