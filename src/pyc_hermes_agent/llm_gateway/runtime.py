"""Minimal OpenAI-compatible execution path for the LLM gateway."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pyc_hermes_agent.contracts import ToolCall
from pyc_hermes_agent.llm_gateway.config import resolve_opencode_like_config
from pyc_hermes_agent.llm_gateway.types import LLMChatChunk, LLMChatRequest, LLMChatResponse, LLMMessage, ProviderConfig, ResolvedLLMConfig


_SUPPORTED_EXECUTION_PROVIDERS = {"openai-compatible", "openrouter"}


def execute_chat(request: LLMChatRequest, root: Path) -> LLMChatResponse:
    resolved = resolve_opencode_like_config(root)
    model_id = request.model or resolved.default_model
    provider_id, provider_config, base_url, provider_headers = _resolve_provider_execution(resolved, model_id)
    payload = _build_chat_payload(model_id, request)
    headers = {
        "Content-Type": "application/json",
        **provider_headers,
    }
    api_key = _resolve_api_key(provider_id, provider_config)
    if api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {api_key}"

    raw_response = _post_with_retry(
        url=f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        payload=payload,
        timeout_seconds=request.timeout_seconds,
        retry_attempts=max(1, request.retry_attempts),
    )
    return _parse_chat_response(raw_response, model_id=model_id, provider_id=provider_id)


def stream_chat(request: LLMChatRequest, root: Path) -> Iterator[LLMChatChunk]:
    resolved = resolve_opencode_like_config(root)
    model_id = request.model or resolved.default_model
    provider_id, provider_config, base_url, provider_headers = _resolve_provider_execution(resolved, model_id)
    payload = _build_chat_payload(model_id, request)
    payload["stream"] = True
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        **provider_headers,
    }
    api_key = _resolve_api_key(provider_id, provider_config)
    if api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {api_key}"

    yield from _stream_chat_completion(
        url=f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        payload=payload,
        timeout_seconds=request.timeout_seconds,
        provider_id=provider_id,
        model_id=model_id,
    )


def _resolve_provider_execution(resolved: ResolvedLLMConfig, model_id: str) -> tuple[str, ProviderConfig | None, str, dict[str, str]]:
    if "/" not in model_id:
        raise ValueError(f"Model id must use provider/model format: {model_id}")
    provider_id, _model_name = model_id.split("/", 1)
    if provider_id not in _SUPPORTED_EXECUTION_PROVIDERS:
        raise ValueError(
            f"Provider '{provider_id}' is not enabled for runtime execution. Supported providers: {sorted(_SUPPORTED_EXECUTION_PROVIDERS)}"
        )
    provider_config = resolved.provider_configs.get(provider_id)
    base_url = _resolve_base_url(provider_id, provider_config)
    headers = _normalize_headers(provider_config.headers if provider_config is not None else {})
    return provider_id, provider_config, base_url, headers


def _resolve_base_url(provider_id: str, provider_config: ProviderConfig | None) -> str:
    configured_base_url = provider_config.base_url if provider_config is not None else None
    if configured_base_url:
        return configured_base_url
    if provider_id == "openai-compatible":
        raise ValueError("Provider 'openai-compatible' requires options.baseURL or options.base_url.")
    if provider_id == "openrouter":
        return "https://openrouter.ai/api/v1"
    raise ValueError(f"Provider '{provider_id}' does not yet support runtime execution without an explicit base URL.")


def _resolve_api_key(provider_id: str, provider_config: ProviderConfig | None) -> str | None:
    option_keys = [
        "apiKey",
        "api_key",
        "token",
        "accessToken",
        "access_token",
    ]
    if provider_config is not None:
        for key in option_keys:
            value = provider_config.options.get(key)
            if isinstance(value, str) and value:
                return value

    env_candidates = [
        f"{provider_id.upper().replace('-', '_')}_API_KEY",
        f"{provider_id.upper().replace('-', '_')}_TOKEN",
    ]
    if provider_id == "openrouter":
        env_candidates.append("OPENROUTER_API_KEY")
    if provider_id == "openai-compatible":
        env_candidates.append("OPENAI_API_KEY")

    for env_name in env_candidates:
        value = os.environ.get(env_name)
        if value:
            return value
    if provider_id == "openrouter":
        raise ValueError("Provider 'openrouter' requires an API key in config options or OPENROUTER_API_KEY.")
    return None


def _normalize_headers(raw_headers: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in raw_headers.items():
        if isinstance(value, str):
            normalized[str(key)] = value
    return normalized


def _build_chat_payload(model_id: str, request: LLMChatRequest) -> dict[str, Any]:
    if not request.messages:
        raise ValueError("Chat request must include at least one message.")
    for message in request.messages:
        if message.role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"Unsupported chat role: {message.role}")
    payload_messages: list[dict[str, Any]] = []
    for message in request.messages:
        payload_messages.append(_serialize_chat_message(message))

    payload: dict[str, Any] = {
        "model": model_id,
        "messages": payload_messages,
    }
    if request.tools:
        payload["tools"] = [_serialize_tool_definition(tool) for tool in request.tools]
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    return payload


def _post_with_retry(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
    retry_attempts: int,
) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retry_attempts):
        request = Request(url, data=encoded, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code != 429:
                detail = exc.read().decode("utf-8", errors="replace")
                raise ValueError(f"LLM provider rejected request: {exc.code} {detail}") from exc
            last_error = exc
        except URLError as exc:
            last_error = exc

        if attempt + 1 < retry_attempts:
            time.sleep(min(0.25 * (attempt + 1), 1.0))

    raise RuntimeError(f"LLM request failed after {retry_attempts} attempt(s): {last_error}") from last_error


def _stream_chat_completion(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
    provider_id: str,
    model_id: str,
) -> Iterator[LLMChatChunk]:
    encoded = json.dumps(payload).encode("utf-8")
    request = Request(url, data=encoded, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_parts: list[str] = []
            pending_tool_calls: dict[int, dict[str, Any]] = {}
            saw_done = False
            for event_payload in _iter_sse_data_lines(response):
                if event_payload == "[DONE]":
                    saw_done = True
                    break
                parsed = json.loads(event_payload)
                chunk = _parse_stream_chunk(
                    parsed,
                    provider_id=provider_id,
                    model_id=model_id,
                    content_parts=content_parts,
                    pending_tool_calls=pending_tool_calls,
                )
                if chunk is not None:
                    yield chunk

            finish_reason = None
            usage: dict[str, Any] = {}
            tool_calls = _materialize_stream_tool_calls(pending_tool_calls)
            if content_parts or tool_calls or saw_done:
                yield LLMChatChunk(
                    event="done",
                    model=model_id,
                    provider_id=provider_id,
                    content="".join(content_parts),
                    tool_calls=tool_calls,
                    finish_reason=finish_reason,
                    usage=usage,
                )
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"LLM streaming request failed: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"LLM streaming request failed: {exc}") from exc


def _iter_sse_data_lines(response: Any) -> Iterator[str]:
    data_lines: list[str] = []
    while True:
        raw_line = response.readline()
        if not raw_line:
            if data_lines:
                yield "\n".join(data_lines)
            break
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())


def _parse_stream_chunk(
    raw_chunk: dict[str, Any],
    *,
    provider_id: str,
    model_id: str,
    content_parts: list[str],
    pending_tool_calls: dict[int, dict[str, Any]],
) -> LLMChatChunk | None:
    choices = raw_chunk.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0]
    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        delta = {}
    delta_text = delta.get("content", "")
    if isinstance(delta_text, list):
        delta_text = "".join(part.get("text", "") for part in delta_text if isinstance(part, dict))
    elif not isinstance(delta_text, str):
        delta_text = str(delta_text or "")
    if delta_text:
        content_parts.append(delta_text)

    _merge_stream_tool_calls(delta.get("tool_calls"), pending_tool_calls)
    finish_reason = first_choice.get("finish_reason")
    if not delta_text and not delta.get("tool_calls") and finish_reason is None:
        return None

    return LLMChatChunk(
        event="delta",
        model=str(raw_chunk.get("model") or model_id),
        provider_id=provider_id,
        delta=delta_text,
        content="".join(content_parts),
        tool_calls=_materialize_stream_tool_calls(pending_tool_calls),
        finish_reason=finish_reason if isinstance(finish_reason, str) or finish_reason is None else str(finish_reason),
        usage=raw_chunk.get("usage", {}) if isinstance(raw_chunk.get("usage"), dict) else {},
        raw_response=raw_chunk,
    )


def _merge_stream_tool_calls(raw_tool_calls: Any, pending_tool_calls: dict[int, dict[str, Any]]) -> None:
    if not isinstance(raw_tool_calls, list):
        return
    for item in raw_tool_calls:
        if not isinstance(item, dict):
            continue
        raw_index = item.get("index", len(pending_tool_calls))
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            index = len(pending_tool_calls)
        existing = pending_tool_calls.get(index)
        if existing is None:
            existing = {
                "id": str(item.get("id") or ""),
                "type": str(item.get("type") or "function"),
                "name": "",
                "arguments": "",
            }
            pending_tool_calls[index] = existing
        if item.get("id"):
            existing["id"] = str(item.get("id"))
        if item.get("type"):
            existing["type"] = str(item.get("type"))
        function_payload = item.get("function")
        if isinstance(function_payload, dict):
            name = function_payload.get("name")
            arguments = function_payload.get("arguments")
            if isinstance(name, str) and name:
                existing["name"] = name
            if isinstance(arguments, str) and arguments:
                existing["arguments"] += arguments


def _materialize_stream_tool_calls(pending_tool_calls: dict[int, dict[str, Any]]) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    for index in sorted(pending_tool_calls):
        call = pending_tool_calls[index]
        if not str(call.get("name", "")).strip():
            continue
        tool_calls.append(
            ToolCall(
                id=str(call.get("id") or ""),
                type=str(call.get("type") or "function"),
                name=str(call.get("name") or "").strip(),
                arguments=str(call.get("arguments") or "{}") or "{}",
            )
        )
    return tool_calls


def _parse_chat_response(raw_response: dict[str, Any], *, model_id: str, provider_id: str) -> LLMChatResponse:
    choices = raw_response.get("choices", [])
    if not choices:
        raise ValueError("LLM response did not include any choices.")
    first_choice = choices[0]
    message = first_choice.get("message", {})
    content = message.get("content", "")
    tool_calls = _parse_tool_calls(message.get("tool_calls"))
    if not isinstance(content, str):
        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
        else:
            content = str(content)
    return LLMChatResponse(
        model=model_id,
        provider_id=provider_id,
        content=content,
        tool_calls=tool_calls,
        finish_reason=first_choice.get("finish_reason"),
        usage=raw_response.get("usage", {}),
        raw_response=raw_response,
    )


def _parse_tool_calls(raw_tool_calls: Any) -> list[ToolCall]:
    if not isinstance(raw_tool_calls, list):
        return []

    tool_calls: list[ToolCall] = []
    for item in raw_tool_calls:
        if not isinstance(item, dict):
            continue
        tool_calls.append(_normalize_tool_call(item))
    return tool_calls


def _serialize_chat_message(message: LLMMessage) -> dict[str, Any]:
    serialized = {
        "role": message.role,
        "content": message.content,
    }
    if message.tool_call_id is not None:
        serialized["tool_call_id"] = message.tool_call_id
    if message.tool_calls:
        serialized["tool_calls"] = [_serialize_tool_call(call) for call in message.tool_calls]
    return serialized


def _serialize_tool_call(call: ToolCall) -> dict[str, Any]:
    normalized = _normalize_tool_call(call)
    return {
        "id": normalized.id,
        "type": normalized.type,
        "function": {
            "name": normalized.name,
            "arguments": normalized.arguments,
        },
    }


def _serialize_tool_definition(tool: Any) -> dict[str, Any]:
    name = str(getattr(tool, "name", "") or "").strip()
    if not name:
        raise ValueError("Tool definition name is required.")

    tool_type = str(getattr(tool, "type", "function") or "function")
    if tool_type != "function":
        raise ValueError(f"Unsupported tool definition type: {tool_type}")

    parameters = getattr(tool, "parameters", None) or {"type": "object", "properties": {}}
    if not isinstance(parameters, dict):
        raise ValueError("Tool definition parameters must be a JSON schema object.")
    parameters = dict(parameters)
    parameters.setdefault("type", "object")
    parameters.setdefault("properties", {})
    if not isinstance(parameters.get("properties"), dict):
        raise ValueError("Tool definition parameters.properties must be an object.")

    function_payload: dict[str, Any] = {
        "name": name,
        "parameters": parameters,
    }
    description = str(getattr(tool, "description", "") or "").strip()
    if description:
        function_payload["description"] = description
    if bool(getattr(tool, "strict", False)):
        function_payload["strict"] = True
    return {
        "type": tool_type,
        "function": function_payload,
    }


def _normalize_tool_call(call: ToolCall | dict[str, Any]) -> ToolCall:
    if isinstance(call, ToolCall):
        if call.type != "function":
            raise ValueError(f"Unsupported tool call type: {call.type}")
        name = call.name.strip()
        if not name:
            raise ValueError("Tool call name is required.")
        return ToolCall(
            id=call.id,
            type=call.type,
            name=name,
            arguments=call.arguments or "{}",
        )

    function_payload = call.get("function")
    if isinstance(function_payload, dict):
        raw_name = function_payload.get("name", "")
        raw_arguments = function_payload.get("arguments", "{}")
    else:
        raw_name = call.get("name", "")
        raw_arguments = call.get("arguments", "{}")

    name = str(raw_name).strip() if raw_name is not None else ""
    if not name:
        raise ValueError("Tool call name is required.")

    call_type = str(call.get("type") or "function")
    if call_type != "function":
        raise ValueError(f"Unsupported tool call type: {call_type}")

    if raw_arguments is None:
        arguments = "{}"
    elif isinstance(raw_arguments, str):
        arguments = raw_arguments or "{}"
    else:
        arguments = json.dumps(raw_arguments, ensure_ascii=True, sort_keys=True)

    return ToolCall(
        id=str(call.get("id") or call.get("tool_call_id") or ""),
        type=call_type,
        name=name,
        arguments=arguments,
    )


__all__ = ["execute_chat", "stream_chat"]
