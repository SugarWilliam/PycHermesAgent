"""Hermes-inspired cross-session recall over local session history."""

from __future__ import annotations

from dataclasses import dataclass

from pyc_hermes_agent.contracts import ChatMessage

from .session_store import AgentSessionRecord, AgentSessionStore


@dataclass(frozen=True, slots=True)
class SessionMessageMatch:
    session_id: str
    model: str = ""
    created_at: str = ""
    updated_at: str = ""
    message_index: int = 0
    role: str = ""
    excerpt: str = ""
    score: int = 0


@dataclass(frozen=True, slots=True)
class SessionRecallMatch:
    session_id: str
    model: str = ""
    created_at: str = ""
    updated_at: str = ""
    message_count: int = 0
    match_count: int = 0
    excerpt: str = ""
    score: int = 0


class SessionRecallStore:
    def __init__(self, root=None, *, session_store: AgentSessionStore | None = None) -> None:
        self._session_store = session_store or AgentSessionStore(root=root)

    def search_messages(self, query: str, *, limit: int = 10) -> list[SessionMessageMatch]:
        normalized_query = query.strip()
        if not normalized_query or limit < 1:
            return []

        terms = _query_terms(normalized_query)
        matches: list[SessionMessageMatch] = []
        for record in self._session_store.list_records():
            matches.extend(_message_matches_for_record(record, normalized_query, terms))

        matches.sort(key=lambda match: (match.score, match.updated_at, match.session_id), reverse=True)
        return matches[:limit]

    def search_sessions(self, query: str, *, limit: int = 5) -> list[SessionRecallMatch]:
        normalized_query = query.strip()
        if not normalized_query or limit < 1:
            return []

        terms = _query_terms(normalized_query)
        matches: list[SessionRecallMatch] = []
        for record in self._session_store.list_records():
            message_matches = _message_matches_for_record(record, normalized_query, terms)
            if not message_matches:
                continue
            best_match = max(message_matches, key=lambda match: match.score)
            matches.append(
                SessionRecallMatch(
                    session_id=record.session_id,
                    model=record.model,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    message_count=len(record.messages),
                    match_count=len(message_matches),
                    excerpt=best_match.excerpt,
                    score=sum(match.score for match in message_matches),
                )
            )

        matches.sort(key=lambda match: (match.score, match.updated_at, match.session_id), reverse=True)
        return matches[:limit]


def _message_matches_for_record(
    record: AgentSessionRecord,
    query: str,
    terms: tuple[str, ...],
) -> list[SessionMessageMatch]:
    matches: list[SessionMessageMatch] = []
    for message_index, message in enumerate(record.messages):
        search_text = _message_search_text(message)
        score = _score_match(search_text, query, terms)
        if score < 1:
            continue
        matches.append(
            SessionMessageMatch(
                session_id=record.session_id,
                model=record.model,
                created_at=record.created_at,
                updated_at=record.updated_at,
                message_index=message_index,
                role=message.role,
                excerpt=_build_excerpt(search_text, query, terms),
                score=score,
            )
        )
    return matches


def _message_search_text(message: ChatMessage) -> str:
    search_parts: list[str] = []
    if message.content.strip():
        search_parts.append(message.content.strip())
    for tool_call in message.tool_calls:
        if tool_call.name:
            search_parts.append(tool_call.name)
        if tool_call.arguments and tool_call.arguments != "{}":
            search_parts.append(tool_call.arguments)
    return "\n".join(search_parts).strip()


def _query_terms(query: str) -> tuple[str, ...]:
    terms = tuple(dict.fromkeys(term.casefold() for term in query.split() if term.strip()))
    if terms:
        return terms
    return (query.casefold(),)


def _score_match(search_text: str, query: str, terms: tuple[str, ...]) -> int:
    if not search_text:
        return 0

    lowered = search_text.casefold()
    normalized_query = query.casefold()
    exact_hits = lowered.count(normalized_query)
    if exact_hits:
        return 100 * exact_hits + len(normalized_query)

    term_hits = sum(lowered.count(term) for term in terms)
    if term_hits < 1:
        return 0
    if len(terms) > 1 and all(term in lowered for term in terms):
        return 50 + term_hits
    return term_hits


def _build_excerpt(search_text: str, query: str, terms: tuple[str, ...], *, limit: int = 160) -> str:
    collapsed = " ".join(search_text.split())
    if len(collapsed) <= limit:
        return collapsed

    lowered = collapsed.casefold()
    match_index = lowered.find(query.casefold())
    if match_index < 0:
        for term in terms:
            match_index = lowered.find(term)
            if match_index >= 0:
                break
    if match_index < 0:
        return collapsed[: limit - 3].rstrip() + "..."

    start = max(0, match_index - (limit // 3))
    end = min(len(collapsed), start + limit)
    excerpt = collapsed[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(collapsed):
        excerpt = excerpt + "..."
    return excerpt


__all__ = ["SessionMessageMatch", "SessionRecallMatch", "SessionRecallStore"]
