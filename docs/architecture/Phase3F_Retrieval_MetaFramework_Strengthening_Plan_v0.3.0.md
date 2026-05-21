# Phase 3F - Retrieval and MetaFramework Strengthening Plan v0.3.0

**Status:** Proposed execution plan
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Parent roadmap:** `docs/architecture/Phase3_Phase4_Productization_Roadmap_v0.3.0.md`
**Goal:** Strengthen grounding quality by improving semantic retrieval, enforcing stronger multi-source evidence-chain validation, and feeding evidence into formal analysis in a clearer, benchmarked, policy-safe way.

---

## 1. Scope

Phase 3F improves the quality of local retrieval and its interaction with `MetaFramework.execute()`.

In scope:

- stronger semantic retrieval than current trigram embeddings
- lexical / semantic / hybrid tuning
- retrieval benchmark expansion
- multi-source evidence convergence and conflict handling
- chain-level validation for multi-hop conclusions
- logic-fallacy and temporal-contradiction detection for evidence-backed outputs
- better evidence packaging into formal analysis
- degraded evidence policies

Out of scope:

- bypassing MetaFramework for formal reasoning
- turning MRAG into a grading engine
- replacing local-first retrieval with cloud-only vector infrastructure

---

## 2. Current Baseline

Current completed baseline includes:

- lexical retrieval
- lightweight deterministic trigram embedding in `mrag_core/embeddings.py`
- SQLite/FTS5 chunk store
- formal analysis mode and benchmark/value-proof foundations in `meta_harness`

Current gap:

- semantic retrieval is still lightweight and heuristic.
- evidence injection into formal analysis is not yet rich enough for stronger grounding claims.
- benchmark coverage for grounding quality is not broad enough.
- multi-source conflicts are not yet first-class structured review objects.
- chain-style conclusions are not yet validated at edge level.
- logic fallacies and timeline contradictions are not yet explicit product checks.

---

## 3. Architecture Rules

- `MetaFramework.execute()` remains the formal-analysis entry point.
- Retrieval evidence is an input to analysis, not its grading authority.
- CE and SR remain separate.
- Provider-native model objects do not flow into retrieval or MetaFramework internals.
- Storage changes must respect manifest/index version controls.
- Multi-source evidence must preserve provenance and source-type distinctions.
- Co-occurrence or naming similarity alone must not be upgraded into causal or implementation certainty.
- Product/config/feature conclusions should prefer code/config/runtime anchors over documentation-only inference when engineering facts are available.

---

## 4. Workstreams

### F1. Semantic Retrieval Upgrade

**Goal:** move beyond the current trigram approximation while preserving local-first operation.

Target files:

- `src/pyc_hermes_agent/mrag_core/embeddings.py`
- `src/pyc_hermes_agent/mrag_core/retrieve.py`
- `src/pyc_hermes_agent/mrag_core/service.py`

Required outcomes:

- Higher-quality embedding path exists.
- Retrieval can distinguish lexical and semantic modes explicitly.

Acceptance:

- Semantic mode is better than trigram-only approximations on representative cases.

### F2. Hybrid Retrieval Tuning

**Goal:** make lexical + semantic retrieval a first-class mode.

Target files:

- `src/pyc_hermes_agent/mrag_core/retrieve.py`
- `src/pyc_hermes_agent/mrag_core/sqlite_store.py`
- `src/pyc_hermes_agent/contracts/*`

Required outcomes:

- Retrieval mode selection is explicit and testable.
- Hybrid ranking behavior is stable and explainable enough for product use.

Acceptance:

- Hybrid mode outperforms lexical-only on a tracked benchmark subset.

### F3. Retrieval Benchmark Expansion

**Goal:** make retrieval quality measurable instead of anecdotal.

Target files:

- `benchmarks/meta_harness/*`
- new retrieval benchmark scripts under `benchmarks/`
- `tests/contract/test_benchmark_15_cases.py` or new benchmark tests

Required outcomes:

- Benchmark cases cover multi-document grounding and ambiguity handling.
- Metrics include retrieval relevance and grounding usefulness.

Acceptance:

- Retrieval changes can be compared reproducibly over time.

### F4. Evidence Convergence and Conflict Handling

**Goal:** make multi-source synthesis explicit instead of silently merged.

Target files:

- `src/pyc_hermes_agent/mrag_core/*`
- `src/pyc_hermes_agent/meta_harness/judge/review.py`
- new evidence-normalization helpers under `src/pyc_hermes_agent/meta_harness/` if needed
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Key assertions can retain source kind and source anchor.
- Conflicting evidence can be represented as structured comparisons instead of silent blending.
- Source precedence is explicit when conflicts cannot be fully resolved.

Acceptance:

- Multi-source outputs can explain conflicts, selected interpretation, and unresolved verification needs.

### F5. Evidence-Chain and Multi-Hop Validation

**Goal:** validate chain-style conclusions instead of treating the final summary as a single opaque claim.

Target files:

- `src/pyc_hermes_agent/meta_harness/kernel/framework.py`
- `src/pyc_hermes_agent/meta_harness/judge/review.py`
- new chain-validation helpers under `src/pyc_hermes_agent/meta_harness/`

Required outcomes:

- Multi-hop claims can be decomposed into directed edges.
- Edge type, source strength, and evidence anchor can be tracked separately.
- Weak or missing edges degrade the confidence of the full chain.

Acceptance:

- A multi-step conclusion can show where its weakest evidentiary link sits.

### F6. Logic and Temporal Consistency Checks

**Goal:** detect flawed reasoning patterns before they harden into formal conclusions.

Target files:

- `src/pyc_hermes_agent/meta_harness/judge/review.py`
- `src/pyc_hermes_agent/meta_harness/quality/*`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Detect circular reasoning, causal reversal, scope drift, and missing requirement-design-implementation-verification links.
- Detect timeline contradictions and dependency-order inconsistencies when evidence includes temporal claims.
- Distinguish confirmed facts from inference-derived statements.

Acceptance:

- Weak logic paths are surfaced as degraded findings, not silently phrased as facts.

### F7. Formal Evidence Packaging

**Goal:** improve how evidence reaches `MetaFramework.execute()`.

Target files:

- `src/pyc_hermes_agent/hermes_engine/agent_loop.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`
- `src/pyc_hermes_agent/meta_harness/kernel/framework.py`
- `src/pyc_hermes_agent/meta_harness/judge/review.py`

Required outcomes:

- Formal analysis receives structured evidence packages instead of loose context alone.
- Evidence packages preserve provenance and degraded-state context.

Acceptance:

- Formal output can explain which evidence informed the result.

### F8. Degraded Evidence Policy

**Goal:** make weak evidence states explicit and non-misleading.

Target files:

- `src/pyc_hermes_agent/meta_harness/quality/*`
- `src/pyc_hermes_agent/meta_harness/judge/review.py`
- `src/pyc_hermes_agent/sidecar_api/services/chat_service.py`

Required outcomes:

- Low-confidence or sparse-evidence cases are labeled clearly.
- Degraded evidence can affect SR/quality wording without collapsing CE/SR separation.

Acceptance:

- Weak grounding is surfaced as degraded, not masked as strong evidence.

---

## 5. Execution Order

Recommended order:

1. F1 - Semantic Retrieval Upgrade
2. F2 - Hybrid Retrieval Tuning
3. F3 - Retrieval Benchmark Expansion
4. F4 - Evidence Convergence and Conflict Handling
5. F5 - Evidence-Chain and Multi-Hop Validation
6. F6 - Logic and Temporal Consistency Checks
7. F7 - Formal Evidence Packaging
8. F8 - Degraded Evidence Policy

---

## 6. Test Plan

Required verification:

- retrieval correctness tests
- benchmark reproducibility tests
- multi-source conflict resolution tests
- chain-validation tests
- logic-fallacy and temporal-consistency tests
- formal evidence integration tests
- degraded-state contract tests

Target test areas:

- `tests/contract/test_mrag_core.py`
- `tests/contract/test_mrag_sqlite.py`
- `tests/contract/test_meta_harness.py`
- `tests/contract/test_meta_harness_value_proof.py`
- new evidence-chain validation test coverage under `tests/contract/`
- new retrieval benchmark test coverage under `tests/contract/`

---

## 7. Risks

| Risk | Impact | Control |
|------|--------|---------|
| Semantic retrieval adds heavy dependencies or drift | Operational complexity | Keep local-first and benchmark every upgrade |
| Multi-source evidence is merged too aggressively | Incorrect conclusions | Structured conflict representation and source precedence |
| Chain-style conclusions hide weak intermediate links | False certainty | Edge-level validation and degraded chain handling |
| Better retrieval leads to overstated formal confidence | Analysis overclaim | Explicit degraded evidence policy |
| Benchmark set is too narrow | False confidence | Expand cases across multi-document tasks |

---

## 8. Exit Definition

Phase 3F is complete when:

- Semantic and hybrid retrieval are first-class and benchmarked.
- Multi-source evidence can be converged, compared, and conflict-labeled structurally.
- Chain-style conclusions expose weak links, logical breaks, and timeline contradictions.
- Formal analysis consumes evidence more structurally.
- Weakly grounded outputs are clearly marked as such.

---
