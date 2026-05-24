"""Lexical and hybrid (lexical + semantic-style) retrieval for MRAG."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, List

from pyc_hermes_agent.contracts import Citation, RetrievalHit, RetrievalRequest, RetrievalResult
from pyc_hermes_agent.mrag_core.document import KnowledgeBase
from pyc_hermes_agent.mrag_core.embedding_backend import resolve_embedding_backend

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]+")


def retrieve(knowledge_base: KnowledgeBase, request: RetrievalRequest) -> RetrievalResult:
    mode = (request.retrieval_mode or "lexical").strip().lower()
    if mode not in {"lexical", "semantic", "hybrid"}:
        return RetrievalResult(
            warnings=[f"Unknown retrieval_mode {request.retrieval_mode!r}; supported: lexical, semantic, hybrid."],
        )

    query_text = (request.query or "").strip()
    if not query_text:
        return RetrievalResult(warnings=["Empty query."])

    query_tokens = _tokenize(query_text)
    if mode == "lexical" and not query_tokens:
        return RetrievalResult(warnings=["Empty query after tokenization."])

    weight = max(0.0, min(1.0, float(request.semantic_weight)))
    if mode == "lexical":
        weight = 0.0
    elif mode == "semantic":
        weight = 1.0

    backend, be_warnings = resolve_embedding_backend(
        workspace_root=Path.cwd(),
        request_override=request.embedding_backend,
    )

    query_embedding = backend.embed_query(query_text)

    lexical_norms: List[float] = []
    semantic_scores: List[float] = []

    if weight > 0.0:
        corpus = [chunk.text for chunk in knowledge_base.chunks]
        chunk_mat = backend.embed_passages(corpus)

        sem_raw: List[float] = []
        for row_idx in range(chunk_mat.shape[0]):
            dot = float(query_embedding @ chunk_mat[row_idx])
            sem_raw.append(max(0.0, min(1.0, dot)))

        semantic_scores.extend(sem_raw)
    else:
        semantic_scores = [0.0 for _ in knowledge_base.chunks]

    for chunk, sem in zip(knowledge_base.chunks, semantic_scores, strict=True):
        chunk_tokens = _tokenize(chunk.text)
        raw_lex = _lexical_score(query_tokens, chunk_tokens) if query_tokens else 0.0
        lexical_norms.append(raw_lex)

    max_lex = max(lexical_norms, default=0.0) or 1.0
    lexical_norms = [s / max_lex for s in lexical_norms]

    scored_hits: List[RetrievalHit] = []
    for chunk, lex_n, sem in zip(knowledge_base.chunks, lexical_norms, semantic_scores, strict=True):
        combined = (1.0 - weight) * lex_n + weight * sem
        if combined <= 0.0:
            continue
        qtoks = query_tokens if query_tokens else [query_text]

        scored_hits.append(
            RetrievalHit(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                score=combined,
                snippet=_snippet(chunk.text, qtoks),
                metadata=dict(chunk.metadata),
            )
        )

    scored_hits.sort(key=lambda hit: hit.score, reverse=True)

    top_hits = scored_hits[: request.top_k]

    citations: List[Citation] = []

    if request.include_citations:
        for hit in top_hits:
            document = knowledge_base.documents.get(hit.document_id)
            section = hit.metadata.get("section")
            normalized_section = section.strip() if isinstance(section, str) else ""
            page = _normalize_page(hit.metadata.get("page"))
            citations.append(
                Citation(
                    document_id=hit.document_id,
                    chunk_id=hit.chunk_id,
                    title=document.title if document else hit.metadata.get("title", ""),
                    source_type=document.source_type if document else hit.metadata.get("source_type", ""),
                    source_uri=document.source_uri if document else hit.metadata.get("source_uri", ""),
                    page=page,
                    section=normalized_section,
                    relevance=hit.score,
                    snippet=hit.snippet,
                )
            )

    coverage = min(1.0, len(top_hits) / max(request.top_k, 1))
    confidence = top_hits[0].score if top_hits else 0.0
    warnings: List[str] = [*be_warnings]

    if mode == "hybrid":
        warnings.append(
            f"Hybrid retrieval: lexical_weight={1.0 - weight:.2f}, semantic_weight={weight:.2f} "
            f"(semantic encoder={backend.name!r}, dim={backend.dim})."
        )

    elif mode == "semantic":
        warnings.append(
            f"Semantic retrieval uses encoder={backend.name!r} (dim={backend.dim}); "
            "install optional ``[mrag-dense]`` and set env for sentence-transformers when needed."
        )
    return RetrievalResult(hits=top_hits, citations=citations, coverage=coverage, confidence=confidence, warnings=warnings)


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _lexical_score(query_tokens: Iterable[str], chunk_tokens: Iterable[str]) -> float:
    query_counter = Counter(query_tokens)
    chunk_counter = Counter(chunk_tokens)
    score = 0.0
    for token, count in query_counter.items():
        if token in chunk_counter:
            score += min(chunk_counter[token], count)
    norm = math.sqrt(sum(query_counter.values()) * max(sum(chunk_counter.values()), 1))
    return score / norm if norm > 0 else 0.0


def _snippet(text: str, query_tokens: Iterable[str], width: int = 160) -> str:
    tokens = list(query_tokens)
    if not tokens:
        return text[:width].strip()
    lowered = text.lower()
    for token in tokens:
        idx = lowered.find(token.lower())
        if idx >= 0:
            start = max(0, idx - width // 3)
            end = min(len(text), idx + width)
            return text[start:end].strip()
    return text[:width].strip()


def _normalize_page(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None
