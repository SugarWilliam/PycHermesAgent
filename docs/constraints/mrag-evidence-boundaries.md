# MRAG Evidence Boundaries

**Status:** Hard constraint

## 1. Ownership

`mrag_core` owns ingestion, parsing, chunking, indexing, retrieval, reranking, evidence packaging, source metadata, and citation fidelity.

## 2. Storage Separation

MRAG storage must remain separate from:

- chat/session memory,
- logs,
- model assets,
- temporary downloads,
- exported artifacts,
- desktop UI state.

Required storage classes:

- source documents,
- manifests,
- indexes,
- retrieval metadata.

## 3. Evidence Boundary

MRAG may provide relevant evidence and citations. It must not assign CE/SR grades or claim method validity. Evidence grading remains in `meta_harness`.

## 4. Persistence Guardrail

The current JSON persistence design requires single-process ownership or an equivalent file-lock guardrail before production release claims. Any writer must respect the guardrail. If ownership cannot be acquired, the sidecar must return a structured storage error rather than writing unsafely.

## 5. Format Evolution

Index format changes require:

- `index_format_version` update,
- migration or rebuild behavior,
- compatibility matrix update,
- restart/persistence tests.

## 6. Retrieval Evolution

The accepted evolution path is:

1. locked JSON MVP,
2. file/url text ingestion surfaces,
3. index version and rebuild semantics,
4. SQLite/FTS5 or vector decision record,
5. optional embeddings and reranking,
6. later multimodal parsing.

No multimodal or semantic retrieval capability may be documented as implemented before tests and contracts exist.
