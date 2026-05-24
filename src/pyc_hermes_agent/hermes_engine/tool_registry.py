"""Minimal tool registry surface for Hermes agent-loop activation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import replace
import json
from typing import Any
from uuid import uuid4

from pyc_hermes_agent.contracts import HermesToolDescriptor, HermesToolsSnapshot, ToolCall, ToolCallResult, ToolDefinition


ToolHandler = Callable[[dict[str, Any]], Any]

_DEFAULT_TOOL_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {},
}


def tool_definition_from_descriptor(
    descriptor: HermesToolDescriptor,
    *,
    description: str = "",
    parameters: Mapping[str, Any] | None = None,
    strict: bool = False,
) -> ToolDefinition:
    details: list[str] = []
    if descriptor.toolset_hints:
        details.append(f"Toolsets: {', '.join(descriptor.toolset_hints)}.")
    if descriptor.requires_env:
        details.append(f"Requires env: {', '.join(descriptor.requires_env)}.")
    resolved_description = description.strip() or " ".join(details).strip()
    return _normalize_tool_definition(
        ToolDefinition(
            name=descriptor.name or descriptor.id,
            description=resolved_description,
            parameters=deepcopy(dict(parameters)) if parameters is not None else deepcopy(_DEFAULT_TOOL_PARAMETERS),
            strict=strict,
        )
    )


def tool_definition_to_openai(definition: ToolDefinition) -> dict[str, Any]:
    normalized = _normalize_tool_definition(definition)
    function_payload: dict[str, Any] = {
        "name": normalized.name,
        "parameters": deepcopy(normalized.parameters),
    }
    if normalized.description:
        function_payload["description"] = normalized.description
    if normalized.strict:
        function_payload["strict"] = True
    return {
        "type": normalized.type,
        "function": function_payload,
    }


def normalize_tool_call(call: ToolCall | Mapping[str, Any]) -> ToolCall:
    if isinstance(call, ToolCall):
        if call.type != "function":
            raise ValueError(f"Unsupported tool call type: {call.type}")
        if not call.name.strip():
            raise ValueError("Tool call name is required.")
        return replace(call, name=call.name.strip(), arguments=call.arguments or "{}")

    function_payload = call.get("function")
    if isinstance(function_payload, Mapping):
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
        id=str(call.get("id") or call.get("tool_call_id") or uuid4()),
        type=call_type,
        name=name,
        arguments=arguments,
    )


def parse_tool_call_arguments(call: ToolCall | Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_tool_call(call)
    try:
        parsed = json.loads(normalized.arguments or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Tool call arguments for '{normalized.name}' must be valid JSON.") from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Tool call arguments for '{normalized.name}' must decode to a JSON object.")
    return parsed


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._descriptors: dict[str, HermesToolDescriptor] = {}
        self._handlers: dict[str, ToolHandler | None] = {}

    @classmethod
    def from_snapshot(cls, snapshot: HermesToolsSnapshot) -> "ToolRegistry":
        registry = cls()
        for descriptor in snapshot.tools:
            registry.register(tool_definition_from_descriptor(descriptor), descriptor=descriptor)
        return registry

    def register(
        self,
        definition: ToolDefinition,
        handler: ToolHandler | None = None,
        *,
        descriptor: HermesToolDescriptor | None = None,
    ) -> HermesToolDescriptor:
        normalized_definition = _normalize_tool_definition(definition)
        existing_descriptor = self._descriptors.get(normalized_definition.name)
        existing_handler = self._handlers.get(normalized_definition.name)
        resolved_handler = handler if handler is not None else existing_handler
        base_descriptor = (
            descriptor
            or existing_descriptor
            or _descriptor_from_definition(
                normalized_definition,
                registered=resolved_handler is not None,
            )
        )
        normalized_descriptor = replace(
            base_descriptor,
            id=base_descriptor.id or normalized_definition.name,
            name=normalized_definition.name,
            registered=base_descriptor.registered or resolved_handler is not None,
            registration_style=base_descriptor.registration_style or "hermes_engine.registry",
        )
        self._definitions[normalized_definition.name] = normalized_definition
        self._descriptors[normalized_definition.name] = normalized_descriptor
        self._handlers[normalized_definition.name] = resolved_handler
        return deepcopy(normalized_descriptor)

    def register_function(
        self,
        name: str,
        handler: ToolHandler,
        *,
        description: str = "",
        parameters: Mapping[str, Any] | None = None,
        descriptor: HermesToolDescriptor | None = None,
        strict: bool = False,
    ) -> HermesToolDescriptor:
        return self.register(
            ToolDefinition(
                name=name,
                description=description,
                parameters=deepcopy(dict(parameters)) if parameters is not None else deepcopy(_DEFAULT_TOOL_PARAMETERS),
                strict=strict,
            ),
            handler=handler,
            descriptor=descriptor,
        )

    def bind_handler(self, name: str, handler: ToolHandler) -> HermesToolDescriptor:
        if name not in self._definitions:
            raise KeyError(f"Tool '{name}' is not registered.")
        self._handlers[name] = handler
        descriptor = self._descriptors[name]
        updated = replace(
            descriptor,
            registered=True,
            registration_style=descriptor.registration_style or "hermes_engine.registry",
        )
        self._descriptors[name] = updated
        return deepcopy(updated)

    def has_tool(self, name: str) -> bool:
        return name in self._definitions

    def list_definitions(self) -> list[ToolDefinition]:
        return [deepcopy(definition) for definition in self._definitions.values()]

    def list_descriptors(self) -> list[HermesToolDescriptor]:
        return [deepcopy(descriptor) for descriptor in self._descriptors.values()]

    def list_openai_tools(self) -> list[dict[str, Any]]:
        return [tool_definition_to_openai(definition) for definition in self._definitions.values()]

    def dispatch(self, call: ToolCall | Mapping[str, Any]) -> ToolCallResult:
        normalized_call = normalize_tool_call(call)
        if normalized_call.name not in self._definitions:
            return _tool_error_result(
                normalized_call,
                code="TOOL_NOT_REGISTERED",
                message=f"Tool '{normalized_call.name}' is not registered.",
            )

        handler = self._handlers.get(normalized_call.name)
        if handler is None:
            return _tool_error_result(
                normalized_call,
                code="TOOL_HANDLER_MISSING",
                message=f"Tool '{normalized_call.name}' does not have a bound handler.",
            )

        try:
            arguments = parse_tool_call_arguments(normalized_call)
        except ValueError as exc:
            return _tool_error_result(
                normalized_call,
                code="TOOL_ARGUMENTS_INVALID",
                message=str(exc),
            )

        try:
            raw_result = handler(arguments)
        except Exception as exc:
            return _tool_error_result(
                normalized_call,
                code="TOOL_EXECUTION_FAILED",
                message=str(exc),
            )
        return _normalize_tool_result(raw_result, normalized_call)


def _normalize_tool_definition(definition: ToolDefinition) -> ToolDefinition:
    name = definition.name.strip()
    if not name:
        raise ValueError("Tool definition name is required.")
    if definition.type != "function":
        raise ValueError(f"Unsupported tool definition type: {definition.type}")

    parameters = deepcopy(definition.parameters) if definition.parameters else deepcopy(_DEFAULT_TOOL_PARAMETERS)
    if not isinstance(parameters, dict):
        raise ValueError("Tool definition parameters must be a JSON schema object.")
    parameters.setdefault("type", "object")
    parameters.setdefault("properties", {})
    if not isinstance(parameters.get("properties"), dict):
        raise ValueError("Tool definition parameters.properties must be an object.")

    return ToolDefinition(
        name=name,
        description=definition.description.strip(),
        parameters=parameters,
        strict=bool(definition.strict),
    )


def _descriptor_from_definition(definition: ToolDefinition, *, registered: bool) -> HermesToolDescriptor:
    return HermesToolDescriptor(
        id=definition.name,
        name=definition.name,
        source="runtime",
        registration_style="hermes_engine.registry",
        registered=registered,
    )


def _tool_error_result(call: ToolCall, *, code: str, message: str) -> ToolCallResult:
    return ToolCallResult(
        tool_call_id=call.id,
        name=call.name,
        content=message,
        is_error=True,
        structured_content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def _normalize_tool_result(raw_result: Any, call: ToolCall) -> ToolCallResult:
    if isinstance(raw_result, ToolCallResult):
        return ToolCallResult(
            tool_call_id=raw_result.tool_call_id or call.id,
            name=raw_result.name or call.name,
            content=raw_result.content,
            is_error=raw_result.is_error,
            structured_content=deepcopy(raw_result.structured_content),
        )

    if isinstance(raw_result, str):
        return ToolCallResult(
            tool_call_id=call.id,
            name=call.name,
            content=raw_result,
        )

    if isinstance(raw_result, Mapping):
        structured_content: dict[str, Any] = deepcopy(dict(raw_result))
    else:
        structured_content = {"result": deepcopy(raw_result)}

    content = _serialize_tool_content(raw_result)
    return ToolCallResult(
        tool_call_id=call.id,
        name=call.name,
        content=content,
        structured_content=structured_content,
    )


def _serialize_tool_content(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return str(value)


__all__ = [
    "ToolHandler",
    "ToolRegistry",
    "normalize_tool_call",
    "parse_tool_call_arguments",
    "tool_definition_from_descriptor",
    "tool_definition_to_openai",
]
