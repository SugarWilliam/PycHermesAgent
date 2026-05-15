# MRAG Evidence Boundaries

| Field | Value |
| --- | --- |
| Date | 2026-05-14 |
| Version | v0.2.0 |
| Author | 彭耀成 |

## Hard Requirements

- `mrag_core` owns ingestion, indexing, retrieval, reranking, and evidence packaging.
- Retrieval results must preserve citations and source references.
- Formal analysis may consume MRAG evidence, but MRAG may not assign CE/SR grades by itself.

## Forbidden Couplings

- No model asset cache mixed into MRAG storage.
- No chat memory mixed into MRAG indexes.
- No renderer-specific formatting assumptions inside retrieval code.

## Storage Rule

Indexes, source files, and artifacts must remain physically separate.
