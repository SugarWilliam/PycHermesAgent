# MetaHarness Boundaries

**Status:** Hard constraint

## 1. Ownership

`meta_harness` owns formal analysis method routing, logic review, reasonableness review, evidence grading, degraded-state annotation, risks, and recommendations.

## 2. Mandatory Entry Point

All formal analysis must enter through:

```python
MetaFramework.execute(request)
```

No feature may bypass this entry point for production behavior.

## 3. Prohibited Responsibilities

`meta_harness` must not own:

- general agent orchestration,
- session state machines,
- tool loop execution,
- provider authentication,
- provider SDK/native response objects,
- Electron UI state,
- MRAG storage implementation,
- vector database internals,
- release automation logic.

## 4. CE/SR Separation

CE and SR must remain separate output dimensions. A predictive or correlational result must never be represented as intervention-grade causal evidence.

## 5. Pluggable Quality Layer Principle

The evaluation report recommendation to make MetaHarness usable as a pluggable quality layer is adopted as a design principle. This does not replace the current product architecture. It means:

- `MetaFramework.execute()` must remain independently callable.
- Inputs and outputs must stay provider-neutral.
- Future LangGraph/OpenAI SDK adapters may call MetaHarness, but cannot become the core product boundary.

## 6. Production Gate

MetaHarness is not production-grade until:

- capability availability reflects real dependency and bridge state,
- routing uses method preconditions and data shape,
- value-proof benchmark compares a simulated LLM-only baseline to `MetaFramework.execute()` outputs (contract-tested),
- degraded-state behavior is tested,
- CE/SR separation is contract-tested.
