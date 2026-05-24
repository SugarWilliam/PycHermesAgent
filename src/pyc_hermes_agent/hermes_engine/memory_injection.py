"""Minimal session-memory injection for the Hermes agent loop."""

from __future__ import annotations

import re

from pyc_hermes_agent.contracts import AgentPlan, ChatMessage


_MEMORY_OPEN_TAG = "<memory-context>"
_MEMORY_CLOSE_TAG = "</memory-context>"
_RECENT_CONVERSATION_LIMIT = 8
_MAX_MEMORY_ITEMS = 6
_MAX_ITEM_LENGTH = 180
_MAX_MEMORY_LENGTH = 1200


def build_prompt_messages(
    messages: list[ChatMessage],
    *,
    plan: AgentPlan | None = None,
    extra_system_messages: list[ChatMessage] | None = None,
) -> list[ChatMessage]:
    system_messages = [_copy_message(message) for message in messages if message.role == "system"]
    conversation_messages = [_copy_message(message) for message in messages if message.role != "system"]
    if plan is not None:
        plan_message = _build_plan_message(plan)
        if plan_message is not None:
            system_messages.append(plan_message)
    if extra_system_messages:
        system_messages.extend(_copy_message(message) for message in extra_system_messages if message.role == "system" and message.content.strip())

    if len(conversation_messages) <= _RECENT_CONVERSATION_LIMIT:
        return [*system_messages, *conversation_messages]

    older_messages = conversation_messages[:-_RECENT_CONVERSATION_LIMIT]
    recent_messages = conversation_messages[-_RECENT_CONVERSATION_LIMIT:]
    memory_message = build_memory_message(older_messages)
    if memory_message is None:
        return [*system_messages, *recent_messages]
    return [*system_messages, memory_message, *recent_messages]


def build_memory_message(messages: list[ChatMessage]) -> ChatMessage | None:
    lines: list[str] = []
    for message in _select_memory_messages(messages):
        snippet = _memory_snippet(message)
        if not snippet:
            continue
        lines.append(f"- {message.role}: {snippet}")

    if not lines:
        return None

    content = "Session memory:\n" + "\n".join(lines)
    content = _truncate(content, _MAX_MEMORY_LENGTH)
    return ChatMessage(role="system", content=f"{_MEMORY_OPEN_TAG}{content}{_MEMORY_CLOSE_TAG}")


def _select_memory_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    informative = [message for message in messages if _memory_snippet(message)]
    return informative[-_MAX_MEMORY_ITEMS:]


def _memory_snippet(message: ChatMessage) -> str:
    text = _collapse_whitespace(_sanitize_memory_text(message.content))
    if text:
        return _truncate(text, _MAX_ITEM_LENGTH)
    if message.tool_calls:
        names = [call.name for call in message.tool_calls if call.name]
        if names:
            return _truncate("requested tools: " + ", ".join(names), _MAX_ITEM_LENGTH)
    return ""


def _sanitize_memory_text(text: str) -> str:
    sanitized = text.replace(_MEMORY_OPEN_TAG, "").replace(_MEMORY_CLOSE_TAG, "")
    return sanitized.strip()


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


def _copy_message(message: ChatMessage) -> ChatMessage:
    return ChatMessage(
        role=message.role,
        content=message.content,
        tool_call_id=message.tool_call_id,
        tool_calls=list(message.tool_calls),
    )


def _build_plan_message(plan: AgentPlan) -> ChatMessage | None:
    if not plan.steps:
        return None

    lines = ["Execution plan:", f"Summary: {plan.summary}"]
    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"{index}. [{step.kind}] {step.description}")
    return ChatMessage(role="system", content="\n".join(lines))


__all__ = ["build_memory_message", "build_prompt_messages"]
