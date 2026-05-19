"""Request normalization helpers for chat and agent loop payloads."""

from __future__ import annotations

from pyc_hermes_agent.contracts import (
    AgentLoopRequest,
    ChatCompletionRequest,
    ChatMessage,
    ToolCall,
    ToolDefinition,
)


def normalize_chat_request(request: ChatCompletionRequest) -> ChatCompletionRequest:
    messages = []
    for message in request.messages:
        if isinstance(message, ChatMessage):
            messages.append(message)
            continue
        if isinstance(message, dict):
            tool_calls = []
            for call in message.get("tool_calls", []):
                if not isinstance(call, dict):
                    raise TypeError(f"Unsupported tool call payload: {type(call)!r}")
                if "function" in call and isinstance(call["function"], dict):
                    function_payload = call["function"]
                    tool_calls.append(
                        ToolCall(
                            id=str(call.get("id", "")),
                            type=str(call.get("type", "function")),
                            name=str(function_payload.get("name", "")),
                            arguments=str(function_payload.get("arguments", "{}")),
                        )
                    )
                    continue
                tool_calls.append(ToolCall(**call))
            messages.append(
                ChatMessage(
                    role=str(message.get("role", "user")),
                    content=str(message.get("content", "")),
                    tool_call_id=str(message["tool_call_id"]) if message.get("tool_call_id") is not None else None,
                    tool_calls=tool_calls,
                )
            )
            continue
        raise TypeError(f"Unsupported chat message payload: {type(message)!r}")

    tools = []
    for tool in request.tools:
        if isinstance(tool, ToolDefinition):
            tools.append(tool)
            continue
        if isinstance(tool, dict):
            if "function" in tool and isinstance(tool["function"], dict):
                function_payload = tool["function"]
                tools.append(
                    ToolDefinition(
                        type=str(tool.get("type", "function")),
                        name=str(function_payload.get("name", "")),
                        description=str(function_payload.get("description", "")),
                        parameters=function_payload.get("parameters", {"type": "object", "properties": {}}),
                        strict=bool(function_payload.get("strict", False)),
                    )
                )
                continue
            tools.append(ToolDefinition(**tool))
            continue
        raise TypeError(f"Unsupported tool definition payload: {type(tool)!r}")

    return ChatCompletionRequest(
        model=request.model,
        messages=messages,
        tools=tools,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        timeout_seconds=request.timeout_seconds,
        retry_attempts=request.retry_attempts,
    )


def normalize_agent_loop_request(request: AgentLoopRequest) -> AgentLoopRequest:
    normalized_chat = normalize_chat_request(
        ChatCompletionRequest(
            model=request.model,
            messages=request.messages,
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout_seconds=request.timeout_seconds,
            retry_attempts=request.retry_attempts,
        )
    )
    return AgentLoopRequest(
        session_id=request.session_id,
        model=normalized_chat.model,
        messages=normalized_chat.messages,
        tools=normalized_chat.tools,
        activated_skills=list(request.activated_skills),
        planning_enabled=request.planning_enabled,
        retry_budget=request.retry_budget,
        temperature=normalized_chat.temperature,
        max_tokens=normalized_chat.max_tokens,
        timeout_seconds=normalized_chat.timeout_seconds,
        retry_attempts=normalized_chat.retry_attempts,
        max_iterations=request.max_iterations,
        analysis_mode=request.analysis_mode,
    )
