"""Minimal local-first session persistence for the Hermes agent loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import ChatMessage, ToolCall
from pyc_hermes_agent.contracts.schemas import utc_now_iso


@dataclass(slots=True)
class AgentSessionRecord:
    session_id: str
    model: str = ""
    created_at: str = ""
    updated_at: str = ""
    messages: list[ChatMessage] = field(default_factory=list)


class AgentSessionStore:
    def __init__(self, root: Path | None = None) -> None:
        runtime_paths = ensure_runtime_directories(resolve_runtime_paths(root))
        self._sessions_root = runtime_paths.local_data_dir / "hermes_engine" / "sessions"
        self._sessions_root.mkdir(parents=True, exist_ok=True)

    def load(self, session_id: str) -> AgentSessionRecord | None:
        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            return None

        session_path = self._session_path(normalized_session_id)
        if not session_path.exists():
            return None

        payload = _read_json(session_path)
        return _record_from_payload(payload, fallback_session_id=normalized_session_id)

    def list_records(self) -> list[AgentSessionRecord]:
        records: list[AgentSessionRecord] = []
        for session_path in self._sessions_root.glob("*.json"):
            records.append(_record_from_payload(_read_json(session_path), fallback_session_id=""))
        records.sort(key=lambda record: (record.updated_at, record.created_at, record.session_id), reverse=True)
        return records

    def save(self, *, session_id: str, model: str, messages: list[ChatMessage], created_at: str | None = None) -> AgentSessionRecord:
        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            raise ValueError("Session id is required.")

        existing = self.load(normalized_session_id)
        record = AgentSessionRecord(
            session_id=normalized_session_id,
            model=model or (existing.model if existing is not None else ""),
            created_at=created_at or (existing.created_at if existing is not None else utc_now_iso()),
            updated_at=utc_now_iso(),
            messages=[_copy_message(message) for message in messages],
        )
        _write_json_atomic(
            self._session_path(normalized_session_id),
            {
                "session_id": record.session_id,
                "model": record.model,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "messages": [asdict(message) for message in record.messages],
            },
        )
        return record

    def resolve_path(self, session_id: str) -> Path:
        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            raise ValueError("Session id is required.")
        return self._session_path(normalized_session_id)

    def _session_path(self, session_id: str) -> Path:
        file_name = sha256(session_id.encode("utf-8")).hexdigest() + ".json"
        return self._sessions_root / file_name


def _copy_message(message: ChatMessage) -> ChatMessage:
    return ChatMessage(
        role=message.role,
        content=message.content,
        tool_call_id=message.tool_call_id,
        tool_calls=[
            ToolCall(id=call.id, type=call.type, name=call.name, arguments=call.arguments)
            for call in message.tool_calls
        ],
    )


def _message_from_payload(payload: dict[str, Any]) -> ChatMessage:
    tool_calls = []
    for item in payload.get("tool_calls", []):
        if isinstance(item, dict):
            tool_calls.append(ToolCall(**item))
    tool_call_id = payload.get("tool_call_id")
    return ChatMessage(
        role=str(payload.get("role", "user")),
        content=str(payload.get("content", "")),
        tool_call_id=str(tool_call_id) if tool_call_id is not None else None,
        tool_calls=tool_calls,
    )


def _record_from_payload(payload: dict[str, Any], *, fallback_session_id: str) -> AgentSessionRecord:
    return AgentSessionRecord(
        session_id=str(payload.get("session_id", fallback_session_id)),
        model=str(payload.get("model", "")),
        created_at=str(payload.get("created_at", "")),
        updated_at=str(payload.get("updated_at", "")),
        messages=[_message_from_payload(item) for item in payload.get("messages", []) if isinstance(item, dict)],
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(path)


__all__ = ["AgentSessionRecord", "AgentSessionStore"]
