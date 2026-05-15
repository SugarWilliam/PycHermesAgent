# PycHermesAgent Detailed Design

| Field | Value |
| --- | --- |
| Date | 2026-05-15 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Detailed Design Aligned to Current Implementation |

## Design Goals

1. Preserve the project boundaries defined in `AGENTS.md`.
2. Give the desktop shell a stable sidecar-facing contract.
3. Reuse Hermes capabilities without importing the upstream runtime directly into the sidecar process.
4. Keep methodology logic inside `meta_harness` and provider/model compatibility inside `llm_gateway`.
5. Keep retrieval and evidence packaging inside `mrag_core`.

## Package Topology

| Package | Design Role | Current Implementation |
| --- | --- | --- |
| `pyc_hermes_agent.sidecar_api` | Stable product-facing Python contract surface | Implemented |
| `pyc_hermes_agent.common` | Shared client helpers and small product-facing convenience wrappers | Implemented |
| `pyc_hermes_agent.hermes_engine` | Hermes runtime seam, tool registry, sync loop, and session/history ownership | Implemented as minimal runtime foundation |
| `pyc_hermes_agent.meta_harness` | Method selection, judgment, quality checks, legacy bridge | Implemented as MVP |
| `pyc_hermes_agent.llm_gateway` | Config/model/provider/rule/skill compatibility and minimal sync execution | Implemented as minimal runtime boundary |
| `pyc_hermes_agent.mrag_core` | Knowledge ingestion and retrieval | Implemented as local-first JSON-backed MVP |
| `pyc_hermes_agent.asset_manager` | Model and runtime assets | Stub |
| `pyc_hermes_agent.artifact_engine` | Exported artifacts | Stub |

## Public Runtime Contracts

Primary dataclass contracts live in `src/pyc_hermes_agent/contracts/schemas.py`.

Important contract families:

1. Task contracts: `TaskRequest`, `TaskResult`
2. Chat and agent runtime contracts: `ChatMessage`, `ChatCompletionRequest`, `ChatCompletionResult`, `ToolDefinition`, `ToolCall`, `ToolCallResult`, `AgentLoopRequest`, `AgentLoopResult`, `AgentPlan`, `PlanStep`
3. Formal analysis contracts: `MetaAnalysisRequest`, `MetaAnalysisResult`
4. Event and error envelopes: `EventEnvelope`, `ErrorEnvelope`
5. Hermes discovery and bridge contracts: `HermesRuntimeSnapshot`, `HermesIntegrationSnapshot`, `Hermes*Snapshot`
6. Retrieval contracts: `RetrievalRequest`, `RetrievalResult`, `Citation`, `RetrievalHit`

Design rule:

- Contracts are the stable boundary.
- Internal implementations may evolve, but these envelopes should remain versioned and predictable.

## Sidecar API Design

The sidecar API is currently implemented in two layers:

1. An importable Python function surface
2. A minimal local HTTP transport

Implemented function entry points in `src/pyc_hermes_agent/sidecar_api/service.py` include:

1. Health and configuration: `get_health`, `get_config_snapshot`
2. Hermes snapshots: `get_hermes_capability_snapshot`, `get_hermes_sessions_snapshot`, `get_hermes_memory_snapshot`, `get_hermes_skills_snapshot`, `get_hermes_tools_snapshot`, `get_hermes_bridge_health`
3. LLM compatibility discovery: `list_providers`, `list_models`, `list_rules`, `list_skills`
4. Formal analysis: `invoke_formal_analysis`
5. Agent runtime: `run_agent_loop`
6. MRAG: `list_knowledge_bases`, `create_knowledge_base`, `ingest_text_document`, `search_knowledge_base`

Implemented HTTP transport entry points in `src/pyc_hermes_agent/sidecar_api/http_server.py` include:

1. `GET /health`
2. `GET /config`
3. `GET /providers`
4. `GET /models`
5. `GET /rules`
6. `GET /skills`
7. `GET /hermes/capability`
8. `GET /hermes/bridge-health`
9. `GET /hermes/sessions`
10. `GET /hermes/memory`
11. `GET /hermes/skills`
12. `GET /hermes/tools`
13. `GET /knowledge-bases`
14. `POST /formal-analysis`
15. `POST /agent/run`
16. `POST /knowledge-bases`
17. `POST /knowledge-bases/{id}/documents/text`
18. `POST /knowledge-bases/{id}/search`

Current design tradeoff:

- The interface is easy to test and now supports a minimal local process boundary over HTTP.
- It is still not a production-complete sidecar process contract.

Current implementation additions:

1. The HTTP transport now emits minimal structured log events for request start and finish.
2. Transport error payloads now carry an explicit top-level `status` field when the request fails.

## Sidecar Client Design

`src/pyc_hermes_agent/common/sidecar_client.py` provides the minimum product client wrapper.

Design rules:

1. `SidecarClient.get_health()` returns the raw health payload.
2. `SidecarClient.get_health_status()` returns a small normalized object for product consumption.
3. Top-level `status_label` is authoritative.
4. Nested `hermes` readiness detail must not be used to reconstruct first-read health.
5. Missing top-level `status_label` collapses to `degraded` only when top-level `degraded` is true; otherwise it collapses to `unavailable`.
6. `SidecarClient` can read health from the local HTTP transport via `base_url`.
7. `SidecarClient.run_agent_loop()` mirrors the sidecar route without moving loop ownership out of `hermes_engine`.

## Hermes Bridge Design

`src/pyc_hermes_agent/hermes_engine/runtime.py` implements a read-only seam around the vendored `upstream/hermes-agent/` checkout.

The design intentionally favors `subprocess-readonly` probing over direct runtime embedding.

Bridged surfaces currently include:

1. Sessions
2. Skills
3. Tools
4. Memory

Design intent:

1. Allow real upstream surface inspection
2. Avoid merging upstream runtime ownership into the sidecar process
3. Keep bridge health and warnings visible through explicit contracts

Current limitation:

- The bridge is good for discovery and readiness reporting, but it is not yet a full conversation runtime adapter.

## Agent Runtime Position

Current repository status:

1. The project is an Agent infrastructure and sidecar skeleton.
2. It now includes a minimal synchronous multi-turn Agent runtime.
3. It is not yet a full production-grade Agent runtime.

Accepted architecture rule:

1. Agent orchestration belongs in `hermes_engine`.
2. `sidecar_api` should expose orchestration, not own it.
3. `meta_harness` should remain an explicit callable capability inside the agent ecosystem rather than becoming the orchestration owner.

Current remaining Agent runtime gaps:

1. Richer planning and decomposition beyond heuristic prompt-time plan injection
2. Richer full-loop streaming beyond assistant text delta passthrough

Current implementation update:

1. A minimal synchronous `AgentLoop` now exists in `src/pyc_hermes_agent/hermes_engine/agent_loop.py`.
2. The current loop is engine-owned and executes a bounded `[LLM -> tool -> re-call]` cycle.
3. Tool definitions and returned tool calls now move through the `llm_gateway` sync execution path.
4. `meta_harness` is now wired into the loop as builtin `formal_analysis` callable capability rather than as orchestration owner.
5. `sidecar_api` and the local HTTP transport now expose the loop but do not own its state machine.
6. `AgentSessionStore` now persists session-backed history under runtime local data.
7. Prompt assembly now injects bounded session memory as fenced system context before the recent live window.
8. Minimal planning and decomposition now exist through heuristic `AgentPlan` generation and execution-plan system-message injection, and callers can disable it per request with `planning_enabled=False`.
9. Minimal reflection and retry budgeting now exist for two bounded recovery cases: empty assistant replies and tool turns where every dispatched tool result is an error.
10. Recovery guidance is injected as transient system context, bounded by `retry_budget`, reported through `retry_count`, and kept inside `hermes_engine` rather than a separate recovery service.
11. `AgentLoop.stream()` now exposes a minimal event stream for loop start, plan emission, token-level assistant text deltas, assistant completion, tool results, retries, done, and error, while `run()` remains a thin wrapper over the same underlying state machine.

## MetaHarness Design

`MetaFramework.execute()` in `src/pyc_hermes_agent/meta_harness/kernel/framework.py` is the only formal-analysis entry point.

Positioning rule:

1. `meta_harness` is currently a configurable method-routing and review harness.
2. It is not currently a general symbolic inference engine.
3. It does not guarantee deterministic logical compensation for weak LLM reasoning.

Execution model:

1. `MethodSelector` chooses a method using keyword and data-shape heuristics.
2. `LegacyMetaBridge` executes the selected method against legacy adapters when data is supplied.
3. `MethodJudge` produces logic and reasonableness review outputs.
4. `QualityChecker` annotates risks, recommendations, and degraded-state validation.

Current design characteristics:

1. Good enough for contract freezing and smoke testing
2. Not good enough for strong method assurance
3. Dependency availability remains under-modeled because `CapabilityRegistry.is_dependency_available()` currently returns `True` for known capabilities

Boundary rule:

1. `meta_harness` does not directly call LLM providers today.
2. If future method routing or review becomes model-assisted, it must go through `llm_gateway` execution interfaces rather than bypassing provider boundaries.
3. If integrated into an Agent loop, `meta_harness` should be invoked as an explicit runtime capability or tool, not as the owner of orchestration state.

## LLM Gateway Design

`llm_gateway` is currently a compatibility and discovery layer.

Boundary rule:

1. `llm_gateway` remains the only layer that may own provider/model execution semantics.
2. Other layers may depend on `llm_gateway` abstractions, but must not embed provider-specific execution logic.

What it resolves today:

1. `opencode.json` and `opencode.jsonc`
2. Provider and model catalogs
3. Free-first sorting
4. Rule discovery from `AGENTS.md`
5. Skill discovery from `.opencode/skills/*/SKILL.md`

What it does not yet own:

1. Broad provider coverage beyond the minimal OpenAI-compatible sync path
2. Rich authentication flows
3. Broad provider streaming execution beyond the minimal OpenAI-compatible SSE path
4. Production-grade retries and rate limiting
5. Runtime model fallback

Current implementation additions:

1. `src/pyc_hermes_agent/llm_gateway/runtime.py` provides a minimal synchronous OpenAI-compatible execution path plus a minimal OpenAI-compatible SSE streaming path.
2. The initial runtime path supports `model`, `messages`, timeout, retry count, configured base URL, API key/header injection, and SSE chunk parsing.
3. The runtime remains intentionally narrow and does not yet change the architectural rule that `llm_gateway` is the sole LLM execution boundary.
4. Runtime execution is explicitly gated to a small provider allowlist rather than implicitly enabling all discovered providers.

Accepted next-step rule for Agent runtime:

1. The first Agent-loop implementation should extend the current synchronous LLM path with tool definitions and parsed tool calls.
2. Richer full-loop streaming beyond assistant text delta passthrough should remain deferred until the synchronous loop and minimal event stream are stable.
3. Tool execution contracts should converge on an OpenAI-compatible function-calling shape where practical.

Current implementation update:

1. `execute_chat()` now accepts tool definitions and parses returned `tool_calls`.
2. `stream_chat()` now parses minimal OpenAI-compatible SSE delta events and emits incremental chunks plus a final done event.
3. `sidecar_api.stream_chat_completion()` and `POST /llm/chat/stream` now expose the streaming path without moving provider semantics out of `llm_gateway`.
4. `hermes_engine` still owns tool dispatch and loop control.

## Agent Loop Streaming Design

The current agent-loop streaming path is hybrid: assistant text and streamed tool-call formation are emitted incrementally, while tool results, retries, and lifecycle updates remain event-oriented.

Current implementation characteristics:

1. `AgentLoop.stream()` emits loop lifecycle events from the same state machine used by `AgentLoop.run()`.
2. Event types currently include start, plan, assistant delta/completed, assistant tool-call delta, tool result, retry, done, and error.
3. The HTTP transport exposes this path as `POST /agent/run/stream` using SSE.
4. Assistant text deltas and streamed tool-call formation now pass through the loop when a streaming LLM executor is available, while tool results, retries, and final result updates remain event-oriented.
5. Each event now carries stable metadata: `event_id` for identity, `trace_id` for stream correlation, `sequence` for ordering, and `is_terminal` for completion semantics.

## MRAG Design

`mrag_core` currently uses an `MRAGService` with optional local JSON persistence.

Flow:

1. Create a knowledge base.
2. Parse text, file, or URL text into a `KnowledgeDocument`.
3. Chunk by character windows.
4. Store documents and chunks in memory.
5. Persist manifests, source documents, and chunk indexes when a storage root is configured.
6. Retrieve using lexical token overlap.
7. Return hits and citations.

Current limitation:

- This is still an MVP evidence path, not a production retrieval subsystem.
- Persistence is JSON-backed and local-first, but there is no production database, migration layer, vector index, or concurrency model.

Current on-disk layout when persistence is enabled:

1. `mrag_core/knowledge_bases/<knowledge_base_id>/manifest.json`
2. `mrag_core/sources/<knowledge_base_id>/<document_id>.json`
3. `mrag_core/indexes/<knowledge_base_id>/chunks.json`

Artifact outputs remain outside the MRAG root and should continue to live under the runtime `artifacts` directory.

## Storage and Packaging Design

Target storage rules come from:

1. `docs/constraints/windows-packaging.md`
2. `docs/constraints/mrag-evidence-boundaries.md`

Target rules:

1. Install directory is read-only.
2. `%APPDATA%` stores configuration.
3. `%LOCALAPPDATA%` stores mutable runtime assets.
4. MRAG indexes, sources, and artifacts remain physically separate.
5. Model downloads require checksum validation and atomic promotion.

Current implementation additions:

1. `src/pyc_hermes_agent/common/runtime_paths.py` resolves sandboxed or OS-backed runtime directories.
2. `MRAGService` now persists knowledge-base manifests, source documents, and chunk indexes under the local MRAG runtime root.

Current implementation gap:

- These rules are documented but not yet implemented end to end in code.

## Concurrency Model

The current sidecar concurrency model is intentionally minimal.

1. The local HTTP transport uses `ThreadingHTTPServer`.
2. The current persistence design assumes single-process ownership of the runtime storage root.
3. There is no cross-process locking, work queue, or migration coordinator yet.
4. JSON-backed MRAG persistence should therefore be treated as engineering-preview storage rather than a concurrent production store.

## Error and Degraded-State Design

The current implementation uses explicit degraded-state reporting in multiple places:

1. Sidecar health reports `degraded` and `status_label`.
2. Formal analysis results report `degraded` and structured risks.
3. Hermes bridge health reports blocked and bridged surfaces.

Current limitation:

- Degraded-state semantics are present, but not yet standardized across a transport boundary, desktop shell, persistent logs, or operator alerts.

Accepted next design step:

1. Keep top-level `status_label` as the canonical readiness signal.
2. Standardize that signal in transport responses, structured logs, and future desktop lifecycle events.

## Skill Lifecycle Design

Current skill support is discovery-oriented rather than execution-oriented.

Current implemented lifecycle:

1. Discover `.opencode/skills/*/SKILL.md`
2. Parse frontmatter metadata
3. Expose skill metadata through `llm_gateway` and `sidecar_api`

Accepted target lifecycle:

1. Discover
2. Parse
3. Normalize
4. Persist or cache metadata if needed
5. Bind at runtime through explicit consumer flows

Current limitation:

- Skills are currently metadata resources, not deeply integrated runtime behaviors inside `meta_harness` or `llm_gateway` execution flows.

## Test Design

Current automated verification lives in `tests/contract/` and focuses on:

1. Contract stability
2. Hermes seam behavior with fake upstream fixtures
3. MetaHarness smoke behavior
4. LLM compatibility resolution
5. MRAG text retrieval behavior
6. Sidecar health and client semantics

Current test gap:

1. No end-to-end desktop tests
2. Only minimal sidecar transport tests
3. Only minimal persistent-storage tests
4. No packaging installer tests
5. No performance or soak tests

## Production Gaps

The most important design gaps before production are:

1. A production-grade sidecar transport and lifecycle model
2. Real LLM provider execution paths
3. Persistent MRAG storage and index management
4. Implemented asset and artifact subsystems
5. End-to-end integration and release validation

## Related Documents

- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/features/PycHermesAgent_Feature_Details_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
