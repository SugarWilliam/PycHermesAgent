"""Session-scoped runtime context helpers for Hermes-derived integrations."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar


_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar("pyc_hermes_agent_session_id", default=None)


def get_current_session_id() -> str | None:
    session_id = _CURRENT_SESSION_ID.get()
    if session_id is None:
        return None
    normalized = session_id.strip()
    return normalized or None


@contextmanager
def bind_session_context(session_id: str | None) -> Iterator[str | None]:
    normalized = (session_id or "").strip() or None
    token = _CURRENT_SESSION_ID.set(normalized)
    try:
        yield normalized
    finally:
        _CURRENT_SESSION_ID.reset(token)


__all__ = ["bind_session_context", "get_current_session_id"]
