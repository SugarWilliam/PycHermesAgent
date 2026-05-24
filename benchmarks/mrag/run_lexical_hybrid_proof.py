#!/usr/bin/env python3
"""Deterministic lexical vs hybrid MRAG ranking smoke (character trigram semantic).

Run from repo root::

    uv run python benchmarks/mrag/run_lexical_hybrid_proof.py

Exit 0 when hybrid top-1 differs from lexical top-1 on the built-in contrast pair
(document A: strong token overlap; document B: rare token + repeated n-gram match).
"""

from __future__ import annotations

from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService


def main() -> int:
    s = MRAGService()
    kb = s.create_knowledge_base("lexical-vs-hybrid-proof")

    doc_a = "AAA BBB common filler words alpha beta gamma delta epsilon zeta eta theta"
    doc_b = "unusualpatternZZZYYY isolated rare token corpus zzz yyy unusualpatternZZZYYY cluster"
    query = "AAA BBB unusualpatternZZZYYY"

    s.ingest_text(kb.knowledge_base_id, doc_a, title="lex-heavy", source_uri="memory://a", source_type="markdown")
    s.ingest_text(kb.knowledge_base_id, doc_b, title="hybrid-shift", source_uri="memory://b", source_type="markdown")

    lex = s.search(kb.knowledge_base_id, RetrievalRequest(query=query, top_k=2, retrieval_mode="lexical"))
    hy = s.search(
        kb.knowledge_base_id,
        RetrievalRequest(query=query, top_k=2, retrieval_mode="hybrid", semantic_weight=0.65),
    )

    if not lex.hits or not hy.hits:
        print("FAILED: missing hits")
        return 2
    lx_top = lex.hits[0].document_id
    hy_top = hy.hits[0].document_id

    if lx_top == hy_top:
        print("FAILED: hybrid did not change top-1 vs lexical")
        print("lexical top:", lx_top, "score", lex.hits[0].score)
        print("hybrid top:", hy_top, "score", hy.hits[0].score)
        return 1

    print("OK: lexical top != hybrid top")
    print("lexical top doc:", lx_top, "score", lex.hits[0].score)
    print("hybrid top doc:", hy_top, "score", hy.hits[0].score)
    if hy.warnings:
        print("hybrid warnings:", hy.warnings[0][:120], "...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
