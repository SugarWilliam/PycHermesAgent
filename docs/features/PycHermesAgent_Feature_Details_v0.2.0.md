# PycHermesAgent Feature Details

| Field | Value |
| --- | --- |
| Date | 2026-05-15 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Feature Inventory for Current Repository State |

## Status Legend

| Status | Meaning |
| --- | --- |
| Implemented | Present in code and covered by contract or smoke tests |
| Partial | Present in code but limited in scope or runtime completeness |
| Planned | Defined in architecture or constraints but not yet implemented |
| Stub | Package placeholder only |

## Product-Facing Entry Points

| Entry Point | Status | Notes |
| --- | --- | --- |
| `pyc_hermes_agent.SidecarClient` | Implemented | Minimal client for top-level sidecar health consumption in-process or over HTTP |
| `pyc_hermes_agent.sidecar_api.*` | Implemented | Function-based sidecar contract surface plus minimal local HTTP transport |
| `pyc_hermes_agent.meta_harness.MetaFramework` | Implemented | Formal analysis entry point |
| `pyc_hermes_agent.hermes_engine.HermesFacade` | Implemented | Hermes inspection and bridge seam |
| `pyc_hermes_agent.resolve_runtime_paths` | Implemented | Runtime path resolution aligned to local-first packaging rules |

## Agent Runtime Status

| Capability | Status | Current Position |
| --- | --- | --- |
| Single LLM invocation | Implemented | Minimal OpenAI-compatible synchronous execution exists |
| Tool-calling loop | Implemented | Minimal synchronous `[LLM -> tool -> re-call]` loop exists in `hermes_engine.AgentLoop` |
| Session-backed multi-turn runtime | Partial | Local session/message history persistence now exists, with resume by `session_id`, but richer runtime ownership is still missing |
| Runtime tool execution | Implemented | `ToolRegistry` dispatches registered tools inside the engine-owned loop |
| Memory injection into prompts | Partial | Older session history is collapsed into a fenced system memory block during prompt assembly | Heuristic only; no provider/plugin memory manager yet |
| Planning / reflection loop | Partial | Minimal heuristic planning and decomposition exist via `AgentPlan` output and prompt-time execution-plan injection; minimal reflection/retry recovery exists for empty replies and all-error tool turns via `retry_budget` and `retry_count` |
| Streaming output | Partial | `llm/chat` supports minimal SSE-based streaming through `llm_gateway`, `sidecar_api`, HTTP transport, and `SidecarClient`; `agent/run` supports assistant text deltas, streamed tool-call formation, and event-oriented tool/retry lifecycle SSE through `AgentLoop.stream()` and `POST /agent/run/stream` |

## Sidecar Health and Diagnostics

| Feature | Entry | Status | Current Behavior | Limitation |
| --- | --- | --- | --- | --- |
| Sidecar health summary | `get_health()` | Implemented | Returns top-level `status_label`, `degraded`, version fields, and Hermes diagnostics | Transport remains minimal |
| Hermes bridge health | `get_hermes_bridge_health()` | Implemented | Reports bridged surfaces, blocked surfaces, warnings, and import readiness | Only covers bridge inspection, not full runtime ownership |
| Minimal health client | `SidecarClient.get_health_status()` | Implemented | Anchors first-read health to top-level `status_label` | Only covers health over HTTP, not the full API surface |
| Minimal local HTTP transport | `create_http_server()`, `serve_http()` | Implemented | Exposes health, config, Hermes snapshots, formal analysis, MRAG, and LLM chat endpoints over loopback HTTP | No auth, no TLS, no supervision, no metrics |
| Agent loop transport exposure | `run_agent_loop()`, `POST /agent/run`, `stream_agent_loop()`, `POST /agent/run/stream` | Implemented | Exposes the engine-owned synchronous agent loop plus assistant text deltas, streamed tool-call formation, and event-oriented SSE updates in-process and over loopback HTTP, including `session_id` resume, `planning_enabled`, `retry_budget`, `event_id`, `trace_id`, `sequence`, and `is_terminal` | No richer full-loop token streaming |
| Structured transport logging | `sidecar_api.logging.log_event()` | Implemented | Emits minimal JSON log events for request and LLM execution boundaries | Not yet a full observability system |

## Hermes Bridge Features

| Feature | Entry | Status | Current Behavior | Limitation |
| --- | --- | --- | --- | --- |
| Capability snapshot | `get_hermes_capability_snapshot()` | Implemented | Reports checkout, commit, worktree, import readiness, and required surfaces | Snapshot only |
| Sessions snapshot | `get_hermes_sessions_snapshot()` | Implemented | Exposes session store metadata and available operations | No session execution runtime adapter |
| Skills snapshot | `get_hermes_skills_snapshot()` | Implemented | Discovers skill metadata and loadability | No full skill execution orchestration |
| Tools snapshot | `get_hermes_tools_snapshot()` | Implemented | Discovers tool registry features and tools | Does not expose production tool loop integration |
| Tool registry | `ToolRegistry` | Implemented | Normalizes tool definitions, OpenAI-style tool calls, and local dispatch | No persistent tool state |
| Sync agent loop | `AgentLoop` | Implemented | Executes bounded synchronous tool-call turns, persists session-backed history, injects bounded memory context, applies heuristic planning when warranted, performs bounded recovery retries for empty replies and all-error tool turns, appends tool results back into model messages, and emits assistant text deltas, streamed tool-call formation, plus event-oriented loop streaming through `stream()` | No richer full-loop token streaming or advanced reflection policy |
| Session store | `AgentSessionStore` | Implemented | Persists agent-loop message history under runtime local data and reloads by `session_id` | Local JSON only; no locking or search surface |
| Memory snapshot | `get_hermes_memory_snapshot()` | Implemented | Reports memory manager and provider metadata | No production memory synchronization layer |

## MetaHarness Features

| Feature | Entry | Status | Current Behavior | Limitation |
| --- | --- | --- | --- | --- |
| Formal analysis invocation | `invoke_formal_analysis()` | Implemented | Wraps `MetaFramework.execute()` and returns events plus analysis | Still synchronous and local |
| Method selection | `MethodSelector.select()` | Partial | Selects methods from task language and data keys | Heuristic only |
| Logic and reasonableness review | `MethodJudge` | Partial | Produces structured review fields | No robust method-specific evaluation pipeline |
| Legacy adapter bridge | `LegacyMetaBridge` | Partial | Executes legacy modules and some numpy fallbacks | Several legacy dependencies remain optional or missing |
| Degraded-state output | `MetaAnalysisResult.degraded` | Implemented | Flags degraded outcomes in analysis results | Policy is still MVP-level |

## LLM Gateway Features

| Feature | Entry | Status | Current Behavior | Limitation |
| --- | --- | --- | --- | --- |
| `opencode` config resolution | `resolve_opencode_like_config()` | Implemented | Loads `opencode.json/jsonc` and resolves providers/models | No runtime execution |
| Free-first model sorting | `sort_models_free_first()` | Implemented | Prioritizes free models in presentation | Presentation only |
| Rule discovery | `discover_rule_files()` and `list_rules()` | Implemented | Discovers `AGENTS.md` and rule files | Discovery only |
| Skill discovery | `load_skill_metadata()` and `list_skills()` | Implemented | Parses `.opencode/skills/*/SKILL.md` metadata | Discovery only |
| Skill runtime binding | None | Planned | Intended future lifecycle after discovery and normalization | Not implemented |
| OpenAI-compatible sync execution | `execute_chat()` | Implemented | Executes synchronous chat completions against a configured OpenAI-compatible `/chat/completions` endpoint | No broad provider breadth yet |
| OpenAI-compatible streaming execution | `stream_chat()` | Partial | Streams minimal SSE chat chunks from a configured OpenAI-compatible `/chat/completions` endpoint and emits delta plus done events | No broad provider breadth, no advanced stream controls |
| Tool-capable sync execution | `execute_chat()` | Implemented | Accepts tool definitions and parses returned `tool_calls` | Still limited to minimal synchronous path |
| Provider execution gating | `execute_chat()` | Implemented | Restricts runtime execution to a small explicit provider set | No broad provider enablement yet |
| Provider runtime execution | Partial | Partial | Minimal runtime exists for explicitly enabled providers | Not yet a broad production execution layer |

## MRAG Features

| Feature | Entry | Status | Current Behavior | Limitation |
| --- | --- | --- | --- | --- |
| Knowledge-base creation | `create_knowledge_base()` | Implemented | Creates a knowledge base and persists it when a runtime storage root is active | Still single-process and MVP-grade |
| Text ingestion | `ingest_text_document()` | Implemented | Parses text, stores chunks, and persists documents/chunk indexes | Text only |
| Retrieval | `search_knowledge_base()` | Implemented | Returns lexical hits and citations | No embeddings or reranking |
| Local JSON persistence | `MRAGService(storage_root=...)` | Implemented | Persists manifests, source documents, and chunk indexes across service restarts | No migration, locking, or production DB |
| File and URL ingest internals | `MRAGService.ingest_file`, `MRAGService.ingest_url_text` | Partial | Available in service layer internals | Not fully surfaced as stable sidecar API |
| Persistent indexes | JSON chunk index files | Partial | Minimal persisted chunk index exists under runtime storage | No vector index or reranking |

## Packaging and Deployment Features

| Feature | Status | Notes |
| --- | --- | --- |
| Windows directory policy | Partial | Runtime path helpers and MRAG storage layout exist, but full packaging flow is not implemented |
| Asset manager | Partial | Local manifest validation, checksum verification, version/index compatibility checks, and staging-directory rename promotion foundation are implemented for local installs; no fsync, durability, or locking guarantee is provided yet, and remote download/upgrade orchestration is still missing |
| Artifact engine | Partial | Local text/JSON artifact export and `TaskResult.artifacts`-compatible metadata helpers are implemented; richer export pipelines and sidecar integration are still missing |
| Electron desktop shell | Planned | Not present in repo |

## Test Coverage Map

| Test Area | Status | Files |
| --- | --- | --- |
| Contract schemas | Implemented | `tests/contract/test_contracts.py` |
| Runtime path management | Implemented | `tests/contract/test_runtime_paths.py` |
| Sidecar API contracts | Implemented | `tests/contract/test_sidecar_api.py` |
| Sidecar client health semantics | Implemented | `tests/contract/test_sidecar_client.py` |
| Sidecar HTTP transport | Implemented | `tests/contract/test_sidecar_http.py` |
| LLM runtime and sidecar process smoke | Implemented | `tests/contract/test_llm_runtime.py` |
| Hermes seam | Implemented | `tests/contract/test_hermes_engine.py` |
| MetaHarness | Implemented | `tests/contract/test_meta_harness.py`, `test_extended_bridge.py`, `test_legacy_bridge.py` |
| LLM compatibility | Implemented | `tests/contract/test_llm_gateway.py`, `test_opencode_compat.py` |
| MRAG MVP | Implemented | `tests/contract/test_mrag_core.py` |
| Asset and artifact helpers | Implemented | `tests/contract/test_asset_manager.py`, `test_artifact_engine.py` |
| Desktop end-to-end | Planned | Not present |
| Packaging/install | Planned | Not present |

## Feature Completeness Summary

| Subsystem | Current Completeness |
| --- | --- |
| Governance and contracts | High |
| Sidecar Python contract surface | High |
| Sidecar local HTTP transport | Medium |
| Hermes bridge seam | Medium |
| MetaHarness MVP | Medium |
| LLM runtime | Low |
| MRAG production readiness | Low-to-medium |
| Packaging/runtime assets | Low |
| Desktop product shell | None |

## Related Documents

- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
- `docs/deployment/PycHermesAgent_Usage_Deployment_Guide_v0.2.0.md`
