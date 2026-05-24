"""Larger deterministic MRAG benchmark: lexical vs hybrid top-1 contrast on synthetic corpora."""

from __future__ import annotations

from dataclasses import dataclass

from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGService


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    key: str
    doc_lex_hits: list[str]
    doc_sem_aligned: list[str]
    query: str
    hybrid_sem_weight: float
    topical_k_overview: list[str]


# Three structurally analogous contrast pairs — larger deterministic surface than single proof pairs (Phase 3F).
DEFAULT_SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        key="token_overlap_vs_trigram_a",
        doc_lex_hits=["AAA BBB common filler alpha beta gamma delta epsilon zeta theta iota"],
        doc_sem_aligned=["zzz raretokenQQQ isolated corpus QQQ repetition raretokenQQQ trigram cluster raretokenQQQ"],
        query="AAA BBB raretokenQQQ",
        hybrid_sem_weight=0.65,
        topical_k_overview=["supporting noise lex doc", "minimal filler lane-b"],
    ),
    ScenarioSpec(
        key="token_overlap_vs_trigram_b",
        doc_lex_hits=["FOO BAR jargon lane one two three four five six seven eight nine ten"],
        doc_sem_aligned=["zzz rareYYYZZ corpus blob YYY repetition rareYYYZZ harmonic rareYYYZZ"],
        query="FOO BAR rareYYYZZ",
        hybrid_sem_weight=0.65,
        topical_k_overview=["template routing backlog noise", "holiday blackout calendar filler"],
    ),
    ScenarioSpec(
        key="token_overlap_vs_trigram_c",
        doc_lex_hits=["PING PONG filler vocab east west north south up down sideways diagonal zigzag"],
        doc_sem_aligned=["qqq iso rareRRRSSS rotor qqq harmonic rareRRRSSS envelope rotor rareRRRSSS"],
        query="PING PONG rareRRRSSS",
        hybrid_sem_weight=0.72,
        topical_k_overview=["warehouse pallet manifest noise", "safety goggles generic bulletin"],
    ),
)


def ingest_scenario_corpus(service: MRAGService, kb_id: str, spec: ScenarioSpec) -> None:
    texts = [*spec.doc_lex_hits, *spec.doc_sem_aligned, *spec.topical_k_overview]
    for idx, blob in enumerate(texts):
        service.ingest_text(
            kb_id,
            blob,
            title=f"{spec.key}-doc-{idx}",
            source_uri=f"benchmark://expanded/{spec.key}/{idx}",
            source_type="markdown",
        )


def scenario_top1_differs_lex_hybrid(service: MRAGService, kb_id: str, spec: ScenarioSpec) -> tuple[bool, str, str]:
    lex = service.search(kb_id, RetrievalRequest(query=spec.query, top_k=8, retrieval_mode="lexical"))
    hy = service.search(
        kb_id,
        RetrievalRequest(
            query=spec.query,
            top_k=8,
            retrieval_mode="hybrid",
            semantic_weight=spec.hybrid_sem_weight,
            include_citations=True,
        ),
    )
    if not lex.hits or not hy.hits:
        lx = lex.hits[0].document_id if lex.hits else ""
        hh = hy.hits[0].document_id if hy.hits else ""
        return False, lx, hh

    lx_top = lex.hits[0].document_id
    hy_top = hy.hits[0].document_id
    return lx_top != hy_top, lx_top, hy_top


def run_expanded_benchmark(
    *,
    scenarios: tuple[ScenarioSpec, ...] = DEFAULT_SCENARIOS,
) -> tuple[int, list[str]]:
    """Return POSIX exit-style code plus log lines (one isolated KB per scenario)."""

    failures = 0
    lines: list[str] = []
    for spec in scenarios:
        svc = MRAGService()
        kb = svc.create_knowledge_base(f"expanded-{spec.key}")
        ingest_scenario_corpus(svc, kb.knowledge_base_id, spec)
        ok, lx, hh = scenario_top1_differs_lex_hybrid(svc, kb.knowledge_base_id, spec)
        lines.append(f"{'OK' if ok else 'FAIL'} scenario={spec.key} lexical_top={lx} hybrid_top={hh}")
        if not ok:
            failures += 1

    if failures:
        lines.insert(
            0,
            "expanded MRAG benchmark: lexical top-1 == hybrid top-1 in "
            f"{failures}/{len(scenarios)} scenario(s) (tune corpus or retrieval weights).",
        )
        return 1, lines
    lines.insert(0, f"OK expanded MRAG benchmark: {len(scenarios)} deterministic scenario(s) diverged lexical vs hybrid.")
    return 0, lines


__all__ = [
    "DEFAULT_SCENARIOS",
    "ScenarioSpec",
    "ingest_scenario_corpus",
    "run_expanded_benchmark",
    "scenario_top1_differs_lex_hybrid",
]
