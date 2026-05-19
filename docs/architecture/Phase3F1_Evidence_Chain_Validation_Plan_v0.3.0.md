# Phase 3F1 - Evidence Chain Validation Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3F_Retrieval_MetaFramework_Strengthening_Plan_v0.3.0.md`
**Goal:** Add a general-purpose evidence-chain verification layer that improves multi-source convergence, chain-level traceability, contradiction handling, logic-fallacy detection, and temporal consistency checks in grounded product outputs.

---

## 1. Scope

This phase extracts broadly useful capabilities for evidence-backed reasoning:

- multi-source evidence normalization
- source precedence and conflict representation
- edge-level validation for chain-style conclusions
- logic-fallacy checks on evidence-backed claims
- timeline and dependency-order consistency checks
- clearer separation between confirmed fact, supported inference, and weak hypothesis

In scope:

- MRAG + code + logs + terminal output + config + dialogue-context convergence
- engineering-fact preference for code/config/runtime anchors when available
- structured unresolved-verification output for weak conclusions

Out of scope:

- turning `meta_harness` into a full theorem prover
- bypassing `MetaFramework.execute()`
- collapsing CE and SR into one confidence number

---

## 2. Generalized Principles Derived for PycHermesAgent

The following generalized capabilities are valuable and reusable across many engineering tasks:

1. **Multi-source semantic convergence**
- When multiple source types contribute to one conclusion, the product should normalize them into a common evidence view before summarizing.

2. **Conflict-first synthesis**
- Contradictory evidence should be surfaced explicitly, not silently averaged or merged.

3. **Source-aware confidence**
- Different evidence sources deserve different default trust roles depending on the question type.

4. **Chain-level verification**
- Multi-hop conclusions should be checked one directed link at a time rather than judged only by the final summary sentence.

5. **Logic-path hygiene**
- The system should detect circular reasoning, causal reversal, scope drift, and broken requirement-to-implementation chains.

6. **Temporal consistency**
- Evidence that includes order, version, stage, or dependency claims should be checked for timeline contradictions.

7. **Confirmed vs inferred separation**
- Final outputs should distinguish what is directly anchored from what is inferred.

---

## 3. Source Classes and Precedence

The system should support source classes such as:

- product-owned knowledge base / MRAG evidence
- current-repo code and configuration
- sidecar/runtime command output from the current session
- archived benchmark or exported reference material
- dialogue-context inference and engineering heuristics

General precedence guidance:

- For engineering behavior, code/config/runtime evidence outranks documentation-only inference.
- For product reference facts, curated KB/MRAG reference material outranks fragmented conversational memory.
- Dialogue-only inference should remain the weakest source class unless independently anchored.

This is not a universal truth ranking. The product should encode a source-precedence policy that is question-aware and still exposes unresolved conflicts.

---

## 4. Chain Validation Model

Multi-hop conclusions should be decomposed into directed edges such as:

- implements / satisfies
- causes / contributes_to
- depends_on / requires
- enables / activates
- maps_to / aliases
- co_occurs_with
- derived_from

The product should treat these edge types differently.

Important robustness rule:

- `co_occurs_with`, naming similarity, parameter resemblance, or temporal proximity alone must not be upgraded into causation, implementation proof, or unique mapping without stronger anchors.

---

## 5. Logic-Fallacy and Consistency Checks

The product should add general checks for:

- circular reasoning
- causal reversal
- scope drift or category substitution
- broken requirement-design-implementation-verification chains
- overclaim from weak evidence
- timeline contradictions
- dependency-order mismatch

These checks should not invent facts. They should downgrade confidence, request verification, or move conclusions into a risk/unresolved section.

---

## 6. Target File Areas

### Evidence normalization and source-aware comparison

- new `src/pyc_hermes_agent/meta_harness/evidence_chain.py`
- new `src/pyc_hermes_agent/meta_harness/source_policy.py`
- `src/pyc_hermes_agent/meta_harness/judge/review.py`

### Chain validation and logic consistency

- new `src/pyc_hermes_agent/meta_harness/consistency.py`
- `src/pyc_hermes_agent/meta_harness/kernel/framework.py`
- `src/pyc_hermes_agent/meta_harness/quality/*`

### Chat / delivery integration

- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

### Retrieval and evidence packaging

- `src/pyc_hermes_agent/mrag_core/*`

### Benchmarks and tests

- `benchmarks/meta_harness/*`
- new `tests/contract/test_evidence_chain_validation.py`
- new `tests/contract/test_logic_temporal_consistency.py`

---

## 7. Workstreams

### EC1. Evidence Normalization

**Goal:** represent evidence from multiple source types in a common structure.

Required outcomes:

- Evidence items preserve source kind, anchor, excerpt, and confidence role.
- Outputs can compare evidence items side by side.

### EC2. Conflict Representation

**Goal:** represent disagreements explicitly.

Required outcomes:

- Conflict table or structured equivalent includes source A, source B, chosen interpretation, unresolved risk, and verification suggestion.
- The system never silently fuses mutually exclusive conclusions.

### EC3. Edge-Level Chain Validation

**Goal:** validate multi-hop reasoning one link at a time.

Required outcomes:

- Directed edges have type, anchor, and source-strength metadata.
- Weak edges degrade the overall chain.

### EC4. Logic and Temporal Checks

**Goal:** identify bad reasoning patterns before final delivery.

Required outcomes:

- Logic-fallacy and timeline-contradiction checks can influence degraded-state messaging.
- Broken chains are surfaced as risks or unresolved verification needs.

### EC5. Delivery Shape and Explainability

**Goal:** make final outputs more usable.

Required outcomes:

- Product can present confirmed facts, inferred conclusions, conflicts, and next verification steps distinctly.
- Strong claims remain attached to anchors.

---

## 8. Test Plan

Required verification:

- multi-source conflict tests
- co-occurrence false-positive tests
- edge-type downgrade tests
- logic-fallacy tests
- temporal inconsistency tests
- final delivery-shape tests for confirmed vs inferred separation

Target test files:

- new `tests/contract/test_evidence_chain_validation.py`
- new `tests/contract/test_logic_temporal_consistency.py`
- updates to `tests/contract/test_meta_harness.py`
- updates to `tests/contract/test_meta_harness_value_proof.py`

---

## 9. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Too much evidence structure makes outputs unreadable | Usability regression | Keep delivery concise but preserve explicit conflict/unresolved sections |
| Heuristic logic checks generate noise | False degradation | Benchmark and tune against representative engineering tasks |
| Source precedence becomes over-rigid | Wrong conclusions in edge cases | Keep precedence policy visible and overridable by stronger anchors |

---

## 10. Exit Definition

Phase 3F1 is complete when:

- Multi-source conclusions preserve source kinds and conflict structure.
- Chain-style reasoning can expose weak links instead of hiding them.
- Logic fallacies and timeline contradictions are surfaced as degraded or unresolved outcomes.
- Final outputs clearly distinguish confirmed facts from inference.

---
