# Phase 3B - Network Search Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Add real-time network search as a grounded evidence source for chat and formal analysis without violating provider, evidence, or MetaFramework boundaries.

---

## 1. Scope

Phase 3B adds internet retrieval to the product runtime as a tool-driven, evidence-oriented capability.

In scope:

- provider-neutral search abstraction
- runtime tool registration for web search
- normalized search result payloads
- sidecar contract surface for tool usage and evidence rendering
- desktop display of network-grounded evidence
- formal-mode use of network evidence through existing formal analysis entry rules

Out of scope:

- autonomous browser control
- arbitrary page action automation
- replacing MRAG with internet search
- allowing provider-native search SDK objects to escape `llm_gateway`

---

## 2. Current Baseline

Current completed baseline includes:

- `AgentLoop` with tool support via `ToolRegistry`
- existing `formal_analysis` tool path in `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- desktop citation and context panel surfaces
- local MRAG retrieval and evidence display

Current gap:

- There is no real internet search tool.
- Desktop has no dedicated network-evidence view.
- Formal mode cannot incorporate real-time external search evidence yet.

---

## 3. Architecture Rules

- Search results are evidence inputs, not truth claims.
- Formal conclusions still route through `MetaFramework.execute()`.
- Search provider implementation must not leak provider-native objects outside `llm_gateway` or tool boundaries.
- Network search results must remain distinguishable from MRAG/local evidence.
- Search failure must degrade gracefully and never stall the agent loop indefinitely.

---

## 4. Workstreams

### B1. Search Provider Abstraction

**Goal:** introduce a provider-neutral search interface that the runtime can depend on safely.

Target files:

- new `src/pyc_hermes_agent/llm_gateway/search.py` or equivalent
- `src/pyc_hermes_agent/llm_gateway/__init__.py`
- new or updated provider config surfaces under `src/pyc_hermes_agent/llm_gateway/*`

Required outcomes:

- Search backend can be switched without changing agent-loop code.
- Search results normalize to stable Python-native structures.
- Auth/config rules remain within gateway-side boundaries.

Acceptance:

- Product runtime depends only on normalized search result objects.

### B2. Runtime Tool Registration

**Goal:** expose search to the agent through a first-class tool.

Target files:

- `src/pyc_hermes_agent/hermes_engine/tool_registry.py`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- new `src/pyc_hermes_agent/hermes_engine/tools/web_search.py`
- `src/pyc_hermes_agent/hermes_engine/planner.py`

Required outcomes:

- AgentLoop can register and call `web_search` or equivalent.
- Tool arguments are validated.
- Planner can recognize when search is appropriate.

Acceptance:

- Search tool callable from chat mode and formal mode.
- Tool failure returns structured errors instead of generic crashes.

### B3. Sidecar Contracts and Serialization

**Goal:** make search-related evidence appear through stable sidecar payloads.

Target files:

- `src/pyc_hermes_agent/contracts/*`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`

Required outcomes:

- Tool-call payloads preserve search metadata.
- Final response payload can include search evidence when relevant.
- Error envelopes cover search-provider failures.

Acceptance:

- Search results and search errors are inspectable from sidecar responses.

### B4. Desktop Evidence Rendering

**Goal:** surface network evidence clearly in the desktop UI.

Target files:

- `desktop/src/components/layout/ContextPanel.jsx`
- `desktop/src/components/context/CitationList.jsx`
- `desktop/src/store/citationStore.js`
- `desktop/src/store/chatStore.js`
- `desktop/src/services/sidecarClient.js`

Required outcomes:

- Network evidence is visually distinct from local KB evidence.
- Users can inspect URL, snippet, and source metadata.
- Search-derived citations do not break existing citation rendering.

Acceptance:

- Desktop shows internet evidence in context/citation UI during or after runs.

### B5. Formal Analysis Grounding

**Goal:** allow formal mode to consume network evidence without violating MetaFramework boundaries.

Target files:

- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/meta_harness/*`
- `src/pyc_hermes_agent/sidecar_api/services/meta_service.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Formal mode can package search evidence into formal requests or formal supporting context.
- The system distinguishes evidence source from evidence grading.
- Search evidence improves grounding without letting external content bypass method review.

Acceptance:

- Formal mode can reference network evidence and still preserve method/evidence separation.

### B6. Failure, Offline, and Policy Handling

**Goal:** keep the product usable under partial failure.

Target files:

- `src/pyc_hermes_agent/sidecar_api/error_domains.py`
- `src/pyc_hermes_agent/hermes_engine/tools/web_search.py`
- desktop UI state files under `desktop/src/store/*`

Required outcomes:

- Empty-result, timeout, offline, auth, and provider-failure cases are all distinct.
- UI shows failures as recoverable conditions.
- Search can be unavailable without breaking the rest of the session.

Acceptance:

- Network failure does not leave the agent loop or desktop in a dead state.

---

## 5. Execution Order

Recommended order:

1. B1 - Search Provider Abstraction
2. B2 - Runtime Tool Registration
3. B3 - Sidecar Contracts and Serialization
4. B4 - Desktop Evidence Rendering
5. B5 - Formal Analysis Grounding
6. B6 - Failure, Offline, and Policy Handling

---

## 6. Test Plan

Required verification:

- new contract tests for search tool request/response behavior
- provider failure and timeout tests
- sidecar serialization tests for tool-call payloads
- desktop evidence rendering tests if available
- formal grounding tests ensuring search evidence does not bypass `MetaFramework.execute()`

Target test areas:

- new `tests/contract/test_web_search.py`
- `tests/contract/test_hermes_agent_loop.py`
- `tests/contract/test_sidecar_api.py`
- `tests/contract/test_sidecar_http.py`
- `tests/integration/test_sidecar_integration.py`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Search provider locks product to one vendor | Portability loss | Provider-neutral abstraction |
| Search evidence gets treated as validated fact | Overclaim risk | Keep grading in `meta_harness` only |
| Search failure blocks chat | Runtime instability | Explicit timeout and degraded handling |
| Desktop evidence UI confuses local and internet sources | User trust loss | Distinct source-type labeling |

---

## 8. Exit Definition

Phase 3B is complete when:

- AgentLoop can use a real-time internet search tool.
- Search evidence is visible in desktop context/citation surfaces.
- Formal analysis can incorporate network evidence without violating architecture boundaries.
- Failure modes are explicit and recoverable.

---
