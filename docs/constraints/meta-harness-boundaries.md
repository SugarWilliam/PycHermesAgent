# MetaHarness Boundaries

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |

## Hard Requirements

- `MetaHarness` is a methodology harness, not a general orchestration runtime.
- Formal analysis must enter through `MetaFramework.execute()`.
- `MetaHarness` must output method rationale, assumptions, evidence grade, risks, and degraded state.
- CE and SR grading must remain separated.

## Forbidden Couplings

- No direct provider auth logic inside `meta_harness`.
- No renderer or Electron state inside `meta_harness`.
- No vector-store table logic inside `meta_harness`.
- No provider-native response objects outside `llm_gateway`.

## Migration Rule

Legacy methodology code is bridged through explicit adapters. It must not become the long-term public runtime API.
