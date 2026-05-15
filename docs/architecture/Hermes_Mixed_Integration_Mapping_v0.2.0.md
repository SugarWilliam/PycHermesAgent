# Hermes Mixed Integration Mapping

| Field | Value |
| --- | --- |
| Date | 2026-05-16 |
| Version | v0.2.0 |
| Author | 彭耀成 |
| Status | Accepted Hermes Integration Mapping |

## Purpose

This document freezes how `PycHermesAgent` should integrate with the vendored `upstream/hermes-agent/` codebase.

It exists to prevent two kinds of implementation drift:

1. Over-embedding upstream Hermes into the product runtime and breaking the current layer boundaries
2. Rebuilding mature Hermes session and memory capabilities from scratch without a deliberate reason

This mapping should be treated as the authoritative answer to the question:

- Which Hermes capabilities are deeply bridged, rebuilt, left as compatibility-only, or kept subprocess-readonly?

## Integration Strategy

The accepted product strategy is `mixed`.

That means:

1. Deeply bridge the Hermes session and memory data-layer concepts that directly support learning and recall
2. Rebuild the main Agent orchestration runtime inside `hermes_engine`
3. Keep provider execution inside `llm_gateway`
4. Keep gateway, CLI, browser, MCP, and other broad upstream runtime surfaces out of the core product runtime unless they are intentionally productized later

## Integration Modes

| Mode | Meaning |
| --- | --- |
| `deep-bridge` | Preserve Hermes capability design and semantics closely, with Pyc-owned implementation boundaries |
| `rebuild` | Re-implement the capability in Pyc ownership because upstream embedding would break architecture or product constraints |
| `compatibility-only` | Preserve discovery or compatibility semantics without adopting the upstream runtime directly |
| `subprocess-readonly` | Keep the upstream surface inspectable or externally callable, but outside the product runtime core |
| `defer` | Explicitly postpone adoption until earlier product milestones are stable |

## Mapping Table

| Capability | Upstream Assets | Current Pyc State | Target Owner | Mode | Target Landing | Target Milestone |
| --- | --- | --- | --- | --- | --- | --- |
| Hermes session store | `hermes_state.py` | Partial local JSON session persistence exists | `hermes_engine` | `deep-bridge` | `hermes_engine.session_store` | `M1` |
| Hermes session recall/search | `hermes_state.py`, `tools/session_search_tool.py` | Not implemented | `hermes_engine` | `deep-bridge` | `hermes_engine.session_recall` | `M2` |
| Hermes session context isolation | `gateway/session_context.py` | Not previously present | `hermes_engine` | `deep-bridge` | `hermes_engine.session_context` | `M1` |
| Hermes session memory summarization | `agent/memory_manager.py` patterns | Minimal local prompt memory injection exists | `hermes_engine` | `rebuild` | `hermes_engine.memory_injection` | Existing / `M1` hardening |
| Hermes long-term memory files | `tools/memory_tool.py` | Not implemented | `hermes_engine` | `deep-bridge` | `hermes_engine.persistent_memory` | `M1` |
| Hermes memory provider abstraction | `agent/memory_provider.py`, `agent/memory_manager.py` | Not implemented | `hermes_engine` | `deep-bridge` | `hermes_engine.memory_providers` | `M2` |
| Hermes Agent loop | `run_agent.py` | Minimal Pyc loop exists | `hermes_engine` | `rebuild` | `hermes_engine.agent_loop` | Existing / `M1` hardening |
| Hermes tool runtime | `model_tools.py`, `tools/registry.py`, `toolsets.py` | Minimal local tool registry exists | `hermes_engine` | `rebuild` | `hermes_engine.tool_registry` | Existing / `M2` expansion |
| Hermes skill discovery | `tools/skills_tool.py`, `agent/skill_utils.py` | Metadata discovery exists | `llm_gateway` | `compatibility-only` | `llm_gateway.skills` | Existing / `M2` hardening |
| Hermes skill runtime activation | `agent/skill_commands.py`, `tools/skills_tool.py` | Not implemented | `llm_gateway` | `rebuild` | `llm_gateway.instruction_loader` | `M2` |
| Hermes project rules/context loading | `agent/prompt_builder.py`, `agent/subdirectory_hints.py` | Path discovery exists, runtime load missing | `llm_gateway` | `compatibility-only` | `llm_gateway.rules`, `llm_gateway.instruction_loader` | `M2` |
| Hermes gateway and messaging platforms | `gateway/`, `hermes_cli/`, `tui_gateway/` | Discovery snapshots only | External / future product layer | `subprocess-readonly` | No core landing in current runtime | `defer` |
| Hermes browser and MCP runtime ecosystem | `tools/browser_tool.py`, `tools/mcp_tool.py`, related runtime packages | Discovery snapshots only | External / future product layer | `subprocess-readonly` | No core landing in current runtime | `defer` |
| Hermes delegation runtime | `tools/delegate_tool.py` | Not implemented | `hermes_engine` | `defer` | Future `hermes_engine` delegation seam | `defer` |

## Capability Notes

### Sessions

The product should inherit Hermes session strengths without embedding the upstream session runtime wholesale.

Implications:

1. Session persistence must graduate from minimal JSON snapshots toward Hermes-like searchable session storage.
2. Session recall should be explicit and queryable rather than only raw message replay.
3. Session lineage and resume semantics should be preserved where useful.

### Memory

Memory integration is split into three layers:

1. Session memory already present in `hermes_engine.memory_injection`
2. Long-term memory files inspired by Hermes `MEMORY.md` and `USER.md`
3. Future memory providers using Hermes-style provider abstractions

The product must not collapse these layers into one untyped memory blob.

### Orchestration

The current `hermes_engine.AgentLoop` remains the correct owner of orchestration.

Accepted rule:

- Do not embed upstream `run_agent.py` as the product runtime.

Reason:

1. It would break the current `hermes_engine` / `llm_gateway` / `meta_harness` separation.
2. It would leak provider and gateway concerns into the wrong layers.
3. It would make long-term maintenance harder than controlled Pyc ownership.

### Skills and Rules

Skill and rule compatibility should remain compatible with the supported `opencode` artifacts while moving toward explicit runtime activation.

Accepted rule:

1. Preserve compatibility semantics in `llm_gateway`
2. Normalize rules and skill instructions there
3. Let `hermes_engine` consume normalized instruction bundles, rather than loading raw compatibility files itself

### External Hermes Runtime Surfaces

The following should stay outside the product runtime core until intentionally productized:

1. CLI and TUI flows
2. Messaging gateways
3. Browser runtime
4. MCP runtime ecosystem
5. Full delegation runtime

These are useful compatibility surfaces, but they are not the first product-defining capabilities for `PycHermesAgent`.

## Immediate Implementation Implications

The first implementation cycle after freezing this mapping should do the following:

1. Add session-scoped runtime context support in `hermes_engine`
2. Prepare a dedicated landing zone for Hermes-derived long-term memory
3. Prepare a dedicated landing zone for Hermes-derived session recall and search
4. Keep Copilot runtime work inside `llm_gateway`
5. Keep rules and explicit skill activation normalization inside `llm_gateway`

## Acceptance Criteria

This mapping should be considered upheld only when all of the following remain true:

1. No product code path embeds upstream `run_agent.py` as the primary runtime owner.
2. Hermes session and memory enhancements land in `hermes_engine`, not in `sidecar_api` or `meta_harness`.
3. Copilot runtime execution remains inside `llm_gateway`.
4. Skills and rules runtime loading are normalized before consumption by `hermes_engine`.
5. New Hermes-related work references one of the capabilities and landing zones in this document.

## Maintenance Rule

Whenever a new Hermes-related capability is added, changed, or intentionally deferred, this mapping must be updated together with:

1. `docs/architecture/Execution_Blueprint_v0.2.0.md`
2. `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
3. `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md` where relevant

## Related Documents

- `docs/architecture/Execution_Blueprint_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Architecture_v0.2.0.md`
- `docs/architecture/PycHermesAgent_Solution_Architecture_v0.2.0.md`
- `docs/architecture/Phase1_Roadmap_v0.2.0.md`
- `docs/design/PycHermesAgent_Detailed_Design_v0.2.0.md`
