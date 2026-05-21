# Phase 3D2 - Rules Runtime Assembly Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3D_Skills_Rules_Runtime_Plan_v0.3.0.md`
**Goal:** Convert rule discovery into a deterministic, inspectable runtime assembly pipeline so system rules, project rules, user rules, and active skills influence the agent in a controlled order.

---

## 1. Scope

Phase 3D2 focuses on rules as runtime inputs rather than just discoverable files.

In scope:

- rule source discovery expansion
- rule precedence definition
- rule assembly into runtime prompt/context
- provenance, audit, and inspection surfaces
- desktop visibility for effective rules

Out of scope:

- arbitrary code execution through rules
- provider-specific rule injection bypassing `llm_gateway`
- rules becoming a general plugin system

---

## 2. Current Baseline

Current completed baseline includes:

- `src/pyc_hermes_agent/llm_gateway/rules.py` discovers `AGENTS.md` or `CLAUDE.md`
- `src/pyc_hermes_agent/sidecar_api/services/common.py` can list discovered rules
- desktop can inspect some runtime state but not effective assembled rule order

Current gap:

- Rules are only discovered, not assembled into a clear runtime chain.
- There is no documented precedence between product/system rules, project rules, user rules, and active skills.
- Effective rule set for a run is not inspectable as a first-class output.

---

## 3. Architecture Rules

- Rule loading and compatibility stay inside `llm_gateway` or product-owned prompt-assembly code.
- Rules influence prompt/context construction, not provider internals.
- Rule order must be deterministic and reviewable.
- Rules must not silently override explicit user instructions.
- Active skills remain a separate concept from rules even if both contribute runtime context.

---

## 4. Workstreams

### R1. Rule Source Expansion

**Goal:** support a broader but controlled set of rule sources.

Target files:

- `src/pyc_hermes_agent/llm_gateway/rules.py`
- `src/pyc_hermes_agent/common/runtime_paths.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`

Required outcomes:

- System/product rules, project rules, and user rules can all be discovered.
- Discovery output includes source kind and path.

Acceptance:

- Runtime can enumerate the available rule layers consistently.

### R2. Rule Precedence and Merge Model

**Goal:** define and encode effective rule ordering.

Target files:

- new `src/pyc_hermes_agent/llm_gateway/rule_assembly.py`
- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`

Required outcomes:

- Precedence model is explicit in code and docs.
- Effective rule stack is assembled the same way every run.

Acceptance:

- Rule order is deterministic and testable.

### R3. Runtime Injection Path

**Goal:** ensure assembled rules actually influence agent behavior in a traceable way.

Target files:

- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/hermes_engine/skill_context.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Effective rules are injected as system/context messages in a stable order.
- Rule injection remains separate from skill injection and user messages.

Acceptance:

- A run can expose which rules were effective and in what order.

### R4. Inspection and Audit Surfaces

**Goal:** make effective rules visible for debugging and trust.

Target files:

- `src/pyc_hermes_agent/sidecar_api/http_server.py`
- `src/pyc_hermes_agent/sidecar_api/services/common.py`
- new audit support if needed under `src/pyc_hermes_agent/hermes_engine/`
- desktop runtime-inspection UI files

Required outcomes:

- Sidecar can return discovered rules and effective rule assembly.
- Desktop can show current rule layers and active precedence.

Acceptance:

- User can inspect the rule set that shaped a run.

### R5. Safety and Override Guarantees

**Goal:** prevent rules from creating opaque or dangerous behavior.

Required outcomes:

- Explicit user instructions remain highest-priority runtime input.
- Ambiguous rule collisions are surfaced rather than silently merged.

Acceptance:

- Rule assembly never hides conflicts that change user-requested behavior unexpectedly.

---

## 5. Execution Order

Recommended order:

1. R1 - Rule Source Expansion
2. R2 - Rule Precedence and Merge Model
3. R3 - Runtime Injection Path
4. R4 - Inspection and Audit Surfaces
5. R5 - Safety and Override Guarantees

---

## 6. Test Plan

Target tests:

- new `tests/contract/test_rules_runtime.py`
- updates to `tests/contract/test_opencode_compat.py`
- updates to `tests/contract/test_sidecar_api.py`
- updates to `tests/contract/test_sidecar_http.py`

Required verification:

- rule discovery by source kind
- deterministic precedence behavior
- effective rule inspection payloads
- explicit-user-instruction override behavior

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Rule precedence is confusing | Debugging difficulty | Single explicit precedence model |
| Rules silently override user intent | Product trust loss | User instruction always highest priority |
| Rule layers bloat prompts excessively | Quality/performance regression | Keep assembly structured and inspectable |

---

## 8. Exit Definition

Phase 3D2 is complete when:

- Rules are assembled into a deterministic runtime chain.
- Effective rules are inspectable from sidecar and desktop surfaces.
- User instructions remain authoritative over rule layers.

---
