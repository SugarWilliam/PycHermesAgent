# MRAG Index Strategy Decision v0.2.0

**Status:** Architecture decision record (ADR)
**Governance:** `docs/Project_Development_and_Release_Governance.md`

## Context

MRAG currently uses JSON-backed chunk stores with lexical retrieval. Phase 1 adds storage ownership locks, manifest fields (`index_format_version`, counts), file/URL ingestion, and rebuild-oriented versioning.

## Decision

1. **Now (v0.2.x preview):** Keep the JSON index MVP as the only supported layout. Increment `index_format_version` in manifests when chunk/manifest layout changes; require explicit rebuild or migration steps documented in the compatibility matrix.
2. **Next:** Evaluate SQLite + FTS5 for structured metadata and better concurrency **after** ownership locks and migration/rebuild semantics are stable in production scenarios.
3. **Later:** Optional embedding + vector indexes remain behind the same storage guardrails; no vector store inside `mrag_core` until migration rules exist.

## Consequences

- Clients must tolerate `index_format_version` bumps and documented rebuild flows.
- Lexical-only retrieval remains the default until a later ADR selects FTS5 or hybrid retrieval.
- This ADR does not authorize mixing MRAG storage with chat memory, model blobs, or logs.
