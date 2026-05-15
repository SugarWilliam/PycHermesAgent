# PycHermesAgent Phase 1 Roadmap

| Field | Value |
| --- | --- |
| Date | 2026-05-15 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Accepted Phase 1 Productization Plan |

## Purpose

This roadmap incorporates the useful parts of the 2026-05-15 external architecture review while correcting statements that are already outdated.

## Recommendation Disposition

| Recommendation Theme | Disposition | Notes |
| --- | --- | --- |
| Keep layered boundaries and contract-first design | Accepted | Already core to the repository and remains a hard requirement |
| Build a localhost sidecar transport first | Accepted and partially completed | Minimal HTTP transport is already implemented and kept as the Phase 1 base |
| Freeze API shape and map Python contracts 1:1 to transport routes | Accepted | Continue evolving HTTP routes as thin wrappers over the Python sidecar API |
| Clarify `meta_harness` as a routing and review harness rather than a full symbolic engine | Accepted | Keep Phase 1 focused on method routing and review outputs, not a new reasoning runtime |
| Prevent `meta_harness` from bypassing `llm_gateway` for any future model-assisted routing | Accepted | `llm_gateway` remains the only LLM execution boundary |
| Implement real LLM execution through an OpenAI-compatible path first | Accepted | This is the highest-value remaining Phase 1 capability gap |
| Add local-first persistence before product claims | Accepted and partially completed | Minimal MRAG JSON persistence and runtime paths are now implemented |
| Standardize health semantics across transport and ops boundaries | Accepted | Current top-level `status_label` remains the canonical readiness signal |
| Define concurrency and locking assumptions explicitly | Accepted | Current JSON persistence remains single-process and engineering-preview only |
| Define a skill lifecycle beyond metadata discovery | Accepted | Runtime binding remains a planned capability, not an implicit behavior |
| Place the future Agent loop in `hermes_engine` rather than `sidecar_api` or `meta_harness` | Accepted | Aligns with project boundaries in `AGENTS.md` |
| Treat `meta_harness` as an explicit callable capability within the Agent ecosystem | Accepted | Keep methodology review separate from orchestration ownership |
| Delay streaming until the synchronous tool loop is stable | Accepted | Phase sequencing is more important than early output polish |
| Introduce unified tool-call semantics before planning/reflection features | Accepted | Tool execution and session state are the next real Agent milestone |
| Add Electron shell now | Deferred | Remains Phase 3 work after sidecar runtime is stronger |
| Adopt FastAPI, `httpx`, `pydantic`, `sqlite-utils` immediately | Not adopted as-is | Current implementation keeps the minimal stdlib transport; dependency expansion will be driven by concrete runtime needs |
| Add OpenAPI immediately | Deferred | Useful, but better after Phase 1 transport routes stabilize |
| Redesign `meta_harness` immediately as a YAML or Jsonnet rule engine | Deferred | Valuable direction, but not before a real LLM execution path and stronger runtime validation exist |

## What Changed Since The External Review

The following claims from the review are now partially outdated:

1. There is now a minimal loopback HTTP sidecar transport.
2. There is now a minimal local-first MRAG persistence layer.
3. Runtime path helpers now align the codebase more closely with the documented `%APPDATA%` and `%LOCALAPPDATA%` boundary model.
4. `numpy` is now declared as a core dependency and the broader scientific stack is modeled as optional extras.
5. There is now a minimal synchronous OpenAI-compatible LLM execution path.

The following review conclusions remain materially true:

1. There is still no broad production-grade LLM execution runtime.
2. There is still no Electron desktop shell.
3. MetaHarness remains heuristic and MVP-grade.
4. Asset and artifact subsystems remain stubs.
5. Production readiness and release readiness are still not achieved.
6. Skill runtime integration is still shallow and metadata-oriented.
7. Concurrency and locking remain explicitly under-designed at production level.
8. There is still no streaming and no advanced reflection/retry policy beyond the minimal heuristic recovery loop.

## Phase 1 Objectives

Phase 1 is now defined as: make the sidecar locally runnable, contract-stable, and able to preserve local state across restarts without claiming production readiness.

## Phase 1 Workstreams

### Workstream A: Sidecar Runtime Boundary

Status:

1. Minimal HTTP transport implemented
2. `SidecarClient` supports in-process and HTTP access for core endpoints

Remaining scope:

1. Add API version routing or explicit version headers
2. Standardize error payloads across all transport failures
3. Add minimal request logging and health-state transition logging
4. Define the future OpenAPI surface after route stabilization
5. Decide how transport health maps to structured log fields and future desktop lifecycle events

Current progress additions:

1. Minimal structured request and LLM execution logging is now implemented.
2. The LLM chat transport path now returns a consistent top-level `status` field on failure.

### Workstream B: Local-First Storage

Status:

1. Runtime path helpers implemented
2. MRAG manifest/source/chunk persistence implemented

Remaining scope:

1. Add migration/version markers for persisted MRAG state
2. Separate source, index, and artifact handling more explicitly
3. Add locking or safe concurrency rules
4. Decide whether to stay on JSON for MVP or move to SQLite in the next phase

### Workstream C: LLM Execution

Status:

1. Config and discovery layer exists
2. Minimal OpenAI-compatible synchronous execution path exists

Next implementation target:

1. Broaden the current execution path beyond the minimal sync baseline
2. Add structured execution error semantics and logging hooks
3. Add controlled provider coverage expansion or clearer provider gating
4. Keep provider-specific objects contained within `llm_gateway`
5. Add streaming only after the sync contract is stable

Current progress additions:

1. Runtime execution now uses explicit provider gating rather than implicit provider enablement.
2. Sync execution path is covered by both in-process and HTTP tests.

### Workstream D: MetaHarness Reliability

Status:

1. Formal analysis entry and output contracts exist
2. Method selection and dependency checks remain heuristic

Remaining scope:

1. Implement real dependency availability checks
2. Strengthen method selection rules without overdesigning the system
3. Improve degraded-state and recommendation outputs
4. Keep `meta_harness` positioned as a routing and review harness unless a later phase intentionally expands its role

### Workstream E: Skills and Rule Resources

Status:

1. Skill discovery and metadata parsing exist
2. Runtime skill binding does not yet exist

Remaining scope:

1. Define the supported skill lifecycle from discovery to runtime binding
2. Keep skills as explicit resources rather than implicit hidden execution paths
3. Decide which subsystem owns runtime skill application in later phases

### Workstream F: Validation

Status:

1. Contract tests are strong for the current codebase shape

Remaining scope:

1. Add persistence-focused sidecar restart tests
2. Add process-level sidecar smoke tests
3. Add real LLM integration tests behind controllable configuration
4. Add packaging and installer tests later in the roadmap

Current progress additions:

1. A minimal process-level sidecar smoke test now covers the LLM chat path.

## Phase 1 Exit Criteria

Phase 1 should be considered complete only when all of the following are true:

1. A stable local sidecar transport is available and documented.
2. The sidecar preserves local MRAG state across restarts.
3. At least one real LLM execution path exists in `llm_gateway`.
4. Core sidecar flows are covered by contract plus process-level smoke tests.
5. The repository remains clearly labeled as an engineering preview, not a production release.

## Phase 2 Preview

Phase 2 will focus on:

1. Hardening transport and health semantics
2. Strengthening MetaHarness
3. Improving asset and artifact subsystems
4. Expanding persistence, validation, and observability

## Phase 2 Agent Runtime Activation

The minimal Agent loop is now activated. The next step is to harden it inside `hermes_engine`.

Planned order:

1. Completed: add a generic tool-call contract and registry surface in `hermes_engine`.
2. Completed: add session persistence and message history ownership in `hermes_engine`.
3. Completed: extend `llm_gateway` synchronous chat execution to accept tool definitions and parse tool calls.
4. Completed: implement a minimal synchronous `AgentLoop` in `hermes_engine`.
5. Completed: expose that loop through `sidecar_api` and the local HTTP transport.
6. Completed: integrate `meta_harness` as an explicit callable capability within the loop rather than as the loop owner.
7. Completed: add bounded session-memory injection during prompt assembly.
8. Completed: add minimal heuristic planning and decomposition via prompt-time plan injection.
9. Completed: add minimal reflection and retry budgeting for recoverable empty replies and all-error tool turns.
10. Completed: add minimal SSE-based streaming for `llm/chat` through `llm_gateway`, `sidecar_api`, HTTP transport, and `SidecarClient`.
11. Completed: add minimal agent-loop event streaming through `hermes_engine.AgentLoop.stream()`, `sidecar_api.stream_agent_loop()`, HTTP SSE, and `SidecarClient`.

Current implementation state:

1. `contracts` now define shared `ToolDefinition`, `ToolCall`, `ToolCallResult`, `AgentLoopRequest`, `AgentLoopResult`, `AgentPlan`, and `PlanStep` shapes.
2. `hermes_engine.tool_registry` now provides the local registry and OpenAI-compatible function shape normalization used by the minimal loop.
3. `hermes_engine.AgentLoop` now executes a synchronous `[LLM -> tool -> re-call]` loop and ships with builtin `formal_analysis` tool registration.
4. `sidecar_api.run_agent_loop()` and `POST /agent/run` now expose the engine-owned loop without moving orchestration ownership into the sidecar layer.
5. `hermes_engine.AgentSessionStore` now persists session-backed message history under runtime local data and the loop can resume by `session_id`.
6. `hermes_engine.memory_injection` now injects bounded session memory into prompt assembly using fenced system context.
7. `hermes_engine.planner` now builds a minimal heuristic execution plan, injects it as a system prompt when warranted, and returns that plan in `AgentLoopResult`.
8. `AgentLoopRequest.planning_enabled` can disable plan injection for callers that need the leaner prompt shape.
9. `AgentLoopRequest.retry_budget` now controls how many guided recovery retries the loop may spend on empty replies and all-error tool turns, and `AgentLoopResult.retry_count` reports how much budget was used.
10. Recovery guidance is injected as transient system context and is not persisted into session history.
11. `llm_gateway.stream_chat()` now supports minimal OpenAI-compatible SSE streaming, and `sidecar_api.stream_chat_completion()` plus `POST /llm/chat/stream` expose that stream to local consumers.
12. `hermes_engine.AgentLoop.stream()` now emits minimal loop events including start, plan, token-level assistant text deltas, streamed tool-call formation, tool results, retries, done, and error without introducing a second orchestration runtime.
13. `sidecar_api.stream_agent_loop()` plus `POST /agent/run/stream` now expose that event stream to local consumers.
14. Loop stream events now carry stable metadata including `event_id`, `trace_id`, monotonic `sequence`, and `is_terminal` for client-side ordering and completion handling.
15. More granular full-loop streaming, especially around tool-call planning and richer provider delta propagation, remains future work.

## Related Documents

- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
