"""Minimal lexical retrieval for the MRAG MVP."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List

from pyc_hermes_agent.contracts import Citation, RetrievalHit, RetrievalRequest, RetrievalResult
from pyc_hermes_agent.mrag_core.document import KnowledgeBase


TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]+")


def retrieve(knowledge_base: KnowledgeBase, request: RetrievalRequest) -> RetrievalResult:
    query_tokens = _tokenize(request.query)
    if not query_tokens:
        return RetrievalResult(warnings=["Empty query after tokenization."])

    scored_hits: List[RetrievalHit] = []
    for chunk in knowledge_base.chunks:
        chunk_tokens = _tokenize(chunk.text)
        if not chunk_tokens:
            continue
        score = _lexical_score(query_tokens, chunk_tokens)
        if score <= 0:
            continue
        scored_hits.append(
            RetrievalHit(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                score=score,
                snippet=_snippet(chunk.text, query_tokens),
                metadata=dict(chunk.metadata),
            )
        )

    scored_hits.sort(key=lambda hit: hit.score, reverse=True)
    top_hits = scored_hits[: request.top_k]

    citations = []
    if request.include_citations:
        for hit in top_hits:
            document = knowledge_base.documents.get(hit.document_id)
            citations.append(
                Citation(
                    document_id=hit.document_id,
                    chunk_id=hit.chunk_id,
                    title=document.title if document else hit.metadata.get("title", ""),
                    source_uri=document.source_uri if document else hit.metadata.get("source_uri", ""),
                    snippet=hit.snippet,
                )
            )

    coverage = min(1.0, len(top_hits) / max(request.top_k, 1))
    confidence = top_hits[0].score if top_hits else 0.0
    return RetrievalResult(hits=top_hits, citations=citations, coverage=coverage, confidence=confidence)


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
    lowered = text.lower()
    for token in query_tokens:
        idx = lowered.find(token.lower())
        if idx >= 0:
            start = max(0, idx - width // 3)
            end = min(len(text), idx + width)
            return text[start:end].strip()
    return text[:width].strip()
