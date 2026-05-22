"""Minimal synchronous Hermes agent loop."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from pyc_hermes_agent.contracts import (
    AgentLoopEvent,
    AgentLoopResult,
    ChatCompletionRequest,
    ChatMessage,
    MetaAnalysisRequest,
    ToolCall,
    ToolCallResult,
    ToolDefinition,
)
from pyc_hermes_agent.hermes_engine.memory_injection import build_prompt_messages
from pyc_hermes_agent.hermes_engine.planner import build_agent_plan
from pyc_hermes_agent.hermes_engine.session_context import bind_session_context
from pyc_hermes_agent.hermes_engine.session_store import AgentSessionStore
from pyc_hermes_agent.hermes_engine.skill_context import SKILLS_RUNTIME_POLICY, build_skill_context_messages
from pyc_hermes_agent.hermes_engine.tool_registry import ToolRegistry
from pyc_hermes_agent.hermes_engine.web_search import run_web_search_tool
from pyc_hermes_agent.llm_gateway import LLMChatChunk, LLMChatRequest, LLMChatResponse, LLMMessage, execute_chat
from pyc_hermes_agent.meta_harness import MetaFramework


LLMExecutor = Callable[[LLMChatRequest, Path], LLMChatResponse]
LLMStreamExecutor = Callable[[LLMChatRequest, Path], Iterator[LLMChatChunk]]
_DEFAULT_MAX_ITERATIONS = 8
_DEFAULT_RETRY_BUDGET = 1
_VALID_ANALYSIS_MODES = ("casual", "structured", "formal")

_STRUCTURED_MODE_SYSTEM_MESSAGE = (
    "You MUST structure your response with the following sections:\n"
    "## Summary\nBrief overview of findings.\n"
    "## Evidence\nKey data points and supporting information.\n"
    "## Risks\nIdentified risks and uncertainties.\n"
    "## Recommendations\nActionable next steps.\n"
    "Do not omit any section."
)


class AgentLoop:
    def __init__(
        self,
        *,
        root: Path | None = None,
        storage_root: Path | None = None,
        llm_executor: LLMExecutor = execute_chat,
        llm_stream_executor: LLMStreamExecutor | None = None,
        tool_registry: ToolRegistry | None = None,
        session_store: AgentSessionStore | None = None,
    ) -> None:
        self._root = (root or Path(__file__).resolve().parents[3]).resolve()
        self._llm_executor = llm_executor
        self._llm_stream_executor = llm_stream_executor
        self._tool_registry = tool_registry or create_meta_harness_tool_registry()
        resolved_storage_root = storage_root if storage_root is not None else root
        self._session_store = session_store or AgentSessionStore(root=resolved_storage_root)

    def run(
        self,
        request: ChatCompletionRequest,
        *,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        session_id: str | None = None,
        planning_enabled: bool = True,
        retry_budget: int = _DEFAULT_RETRY_BUDGET,
        activated_skills: list[str] | None = None,
        analysis_mode: str = "casual",
    ) -> AgentLoopResult:
        generator = self._run_generator(
            request,
            tool_registry=tool_registry,
            max_iterations=max_iterations,
            session_id=session_id,
            planning_enabled=planning_enabled,
            retry_budget=retry_budget,
            stream_llm_tokens=False,
            activated_skills=activated_skills,
            analysis_mode=analysis_mode,
        )
        while True:
            try:
                next(generator)
            except StopIteration as stop:
                result = stop.value
                if isinstance(result, AgentLoopResult):
                    return result
                raise RuntimeError("Agent loop terminated without a final result.")

    def stream(
        self,
        request: ChatCompletionRequest,
        *,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        session_id: str | None = None,
        planning_enabled: bool = True,
        retry_budget: int = _DEFAULT_RETRY_BUDGET,
        activated_skills: list[str] | None = None,
        analysis_mode: str = "casual",
    ) -> Iterator[AgentLoopEvent]:
        yield from self._run_generator(
            request,
            tool_registry=tool_registry,
            max_iterations=max_iterations,
            session_id=session_id,
            planning_enabled=planning_enabled,
            retry_budget=retry_budget,
            stream_llm_tokens=True,
            activated_skills=activated_skills,
            analysis_mode=analysis_mode,
        )

    def _run_generator(
        self,
        request: ChatCompletionRequest,
        *,
        tool_registry: ToolRegistry | None,
        max_iterations: int,
        session_id: str | None,
        planning_enabled: bool,
        retry_budget: int,
        stream_llm_tokens: bool,
        activated_skills: list[str] | None,
        analysis_mode: str = "casual",
    ) -> Generator[AgentLoopEvent, None, AgentLoopResult]:
        if max_iterations < 1:
            raise ValueError("Agent loop max_iterations must be at least 1.")
        if retry_budget < 0:
            raise ValueError("Agent loop retry_budget cannot be negative.")
        if analysis_mode not in _VALID_ANALYSIS_MODES:
            raise ValueError(f"Invalid analysis_mode '{analysis_mode}'. Must be one of: {', '.join(_VALID_ANALYSIS_MODES)}")

        resolved_session_id = (session_id or "").strip() or str(uuid4())
        with bind_session_context(resolved_session_id):
            existing_session = self._session_store.load(resolved_session_id)
        existing_messages = [_normalize_chat_message(message) for message in existing_session.messages] if existing_session else []
        new_messages = [_normalize_chat_message(message) for message in request.messages]
        if not new_messages:
            raise ValueError("Agent loop requires at least one new message.")
        messages = [*existing_messages, *new_messages]

        registry = tool_registry or self._tool_registry
        tools = _resolve_loop_tools(request, registry)
        plan = build_agent_plan(messages, tools) if planning_enabled else None
        normalized_activated_skills = [name.strip() for name in (activated_skills or []) if name.strip()]
        skill_messages = build_skill_context_messages(self._root, activated_skills)
        tool_results: list[ToolCallResult] = []
        last_response = LLMChatResponse()
        active_model = request.model or (existing_session.model if existing_session is not None else "")
        retry_count = 0
        recovery_message: ChatMessage | None = None
        current_iteration = 0
        trace_id = str(uuid4())
        sequence = 0

        def emit(
            event: str,
            *,
            model: str = "",
            provider_id: str = "",
            iteration: int = 0,
            retry_count: int = 0,
            delta: str = "",
            content: str = "",
            tool_calls: list[Any] | None = None,
            finish_reason: str | None = None,
            payload: dict[str, Any] | None = None,
            error: dict[str, Any] | None = None,
            is_terminal: bool = False,
        ) -> AgentLoopEvent:
            nonlocal sequence
            sequence += 1
            return AgentLoopEvent(
                trace_id=trace_id,
                sequence=sequence,
                event=event,
                is_terminal=is_terminal,
                session_id=resolved_session_id,
                model=model,
                provider_id=provider_id,
                iteration=iteration,
                retry_count=retry_count,
                delta=delta,
                content=content,
                tool_calls=list(tool_calls or []),
                finish_reason=finish_reason,
                payload=payload or {},
                error=error or {},
            )

        yield emit(
            "start",
            model=active_model,
            retry_count=retry_count,
            payload={
                "max_iterations": max_iterations,
                "planning_enabled": planning_enabled,
                "retry_budget": retry_budget,
                "activated_skills": normalized_activated_skills,
                "skills_runtime_policy": dict(SKILLS_RUNTIME_POLICY),
                "analysis_mode": analysis_mode,
            },
        )
        if plan is not None:
            yield emit("plan", model=active_model, retry_count=retry_count, payload={"plan": plan})

        try:
            for iteration in range(1, max_iterations + 1):
                current_iteration = iteration
                with bind_session_context(resolved_session_id):
                    extra_system_messages = [*skill_messages]
                    if analysis_mode == "structured":
                        extra_system_messages.append(ChatMessage(role="system", content=_STRUCTURED_MODE_SYSTEM_MESSAGE))
                    if recovery_message is not None:
                        extra_system_messages.append(recovery_message)
                    prompt_messages = build_prompt_messages(
                        messages,
                        plan=plan,
                        extra_system_messages=extra_system_messages,
                    )
                recovery_message = None
                llm_request = LLMChatRequest(
                    model=active_model,
                    messages=[_to_llm_message(message) for message in prompt_messages],
                    tools=tools,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    timeout_seconds=request.timeout_seconds,
                    retry_attempts=request.retry_attempts,
                )
                emitted_text_deltas = False
                if stream_llm_tokens:
                    last_response, emitted_text_deltas = yield from self._stream_llm_turn(
                        llm_request,
                        session_id=resolved_session_id,
                        iteration=iteration,
                        retry_count=retry_count,
                        emit_event=emit,
                    )
                else:
                    with bind_session_context(resolved_session_id):
                        last_response = self._llm_executor(llm_request, self._root)
                if last_response.model:
                    active_model = last_response.model

                if _should_retry_empty_response(last_response) and retry_count < retry_budget:
                    retry_count += 1
                    recovery_message = _build_empty_response_recovery_message(retry_count=retry_count, retry_budget=retry_budget)
                    yield emit(
                        "retry",
                        model=active_model,
                        provider_id=last_response.provider_id,
                        iteration=iteration,
                        retry_count=retry_count,
                        payload={
                            "reason": "empty_response",
                            "recovery_message": recovery_message.content,
                        },
                    )
                    continue

                assistant_message = ChatMessage(
                    role="assistant",
                    content=last_response.content,
                    tool_calls=list(last_response.tool_calls),
                )
                messages.append(assistant_message)

                if last_response.content and not emitted_text_deltas:
                    yield emit(
                        "assistant.delta",
                        model=active_model,
                        provider_id=last_response.provider_id,
                        iteration=iteration,
                        retry_count=retry_count,
                        delta=last_response.content,
                        content=last_response.content,
                    )

                yield emit(
                    "assistant.completed",
                    model=active_model,
                    provider_id=last_response.provider_id,
                    iteration=iteration,
                    retry_count=retry_count,
                    content=last_response.content,
                    tool_calls=list(last_response.tool_calls),
                    finish_reason=last_response.finish_reason,
                    payload={"raw_response": last_response.raw_response},
                )

                if not last_response.tool_calls:
                    # In formal mode, auto-inject formal_analysis if it wasn't called this session.
                    if analysis_mode == "formal" and not _has_formal_analysis_call(tool_results):
                        auto_tool_call = ToolCall(
                            name="formal_analysis",
                            arguments='{"problem_statement": ' + _json_escape(last_response.content or "Analyze the conversation context.") + "}",
                        )
                        with bind_session_context(resolved_session_id):
                            auto_result = registry.dispatch(auto_tool_call)
                        tool_results.append(auto_result)
                        messages.append(ChatMessage(role="tool", content=auto_result.content, tool_call_id=auto_result.tool_call_id))
                        yield emit(
                            "tool.result",
                            model=active_model,
                            provider_id=last_response.provider_id,
                            iteration=iteration,
                            retry_count=retry_count,
                            payload={"tool_call": auto_tool_call, "tool_result": auto_result, "auto_injected": True},
                        )
                        # Continue loop so LLM can incorporate the formal analysis result.
                        continue

                    with bind_session_context(resolved_session_id):
                        self._persist_session(resolved_session_id, active_model, messages, existing_session)
                    result = AgentLoopResult(
                        session_id=resolved_session_id,
                        model=active_model,
                        provider_id=last_response.provider_id,
                        content=last_response.content,
                        finish_reason=last_response.finish_reason,
                        iterations=iteration,
                        retry_count=retry_count,
                        plan=plan,
                        messages=messages,
                        tool_results=tool_results,
                        raw_response=last_response.raw_response,
                    )
                    yield emit(
                        "done",
                        model=active_model,
                        provider_id=last_response.provider_id,
                        iteration=iteration,
                        retry_count=retry_count,
                        content=last_response.content,
                        finish_reason=last_response.finish_reason,
                        payload={"result": result},
                        is_terminal=True,
                    )
                    return result

                turn_tool_results: list[ToolCallResult] = []
                for tool_call in last_response.tool_calls:
                    with bind_session_context(resolved_session_id):
                        tool_result = registry.dispatch(tool_call)
                    tool_results.append(tool_result)
                    turn_tool_results.append(tool_result)
                    messages.append(
                        ChatMessage(
                            role="tool",
                            content=tool_result.content,
                            tool_call_id=tool_result.tool_call_id,
                        )
                    )
                    yield emit(
                        "tool.result",
                        model=active_model,
                        provider_id=last_response.provider_id,
                        iteration=iteration,
                        retry_count=retry_count,
                        payload={
                            "tool_call": tool_call,
                            "tool_result": tool_result,
                        },
                    )

                if retry_count < retry_budget:
                    recovery_message = _build_tool_error_recovery_message(
                        turn_tool_results,
                        retry_count=retry_count + 1,
                        retry_budget=retry_budget,
                    )
                    if recovery_message is not None:
                        retry_count += 1
                        yield emit(
                            "retry",
                            model=active_model,
                            provider_id=last_response.provider_id,
                            iteration=iteration,
                            retry_count=retry_count,
                            payload={
                                "reason": "tool_error",
                                "recovery_message": recovery_message.content,
                            },
                        )
        except Exception as exc:
            with bind_session_context(resolved_session_id):
                self._persist_session(resolved_session_id, active_model, messages, existing_session)
            yield emit(
                "error",
                model=active_model,
                iteration=current_iteration,
                retry_count=retry_count,
                error={
                    "message": str(exc),
                    "type": exc.__class__.__name__,
                },
                is_terminal=True,
            )
            raise

        raise RuntimeError("Agent loop exceeded max_iterations without reaching a final assistant response.")

    def _stream_llm_turn(
        self,
        request: LLMChatRequest,
        *,
        session_id: str,
        iteration: int,
        retry_count: int,
        emit_event: Callable[..., AgentLoopEvent],
    ) -> Generator[AgentLoopEvent, None, tuple[LLMChatResponse, bool]]:
        if self._llm_stream_executor is None:
            with bind_session_context(session_id):
                return self._llm_executor(request, self._root), False

        saw_chunk = False
        emitted_text_deltas = False
        model = request.model
        provider_id = ""
        content = ""
        tool_calls = []
        finish_reason = None
        usage: dict[str, Any] = {}
        raw_response: dict[str, Any] = {}
        tool_call_state_key: tuple[tuple[str, str, str, str], ...] = ()

        with bind_session_context(session_id):
            stream_iterator = iter(self._llm_stream_executor(request, self._root))

        while True:
            try:
                with bind_session_context(session_id):
                    chunk = next(stream_iterator)
            except StopIteration:
                break

            saw_chunk = True
            if chunk.event == "error":
                raise RuntimeError(_stream_error_message(chunk))
            if chunk.model:
                model = chunk.model
            if chunk.provider_id:
                provider_id = chunk.provider_id
            if chunk.delta:
                emitted_text_deltas = True
            if chunk.content:
                content = chunk.content
            elif chunk.delta:
                content += chunk.delta
            if chunk.tool_calls:
                tool_calls = list(chunk.tool_calls)
            if chunk.finish_reason is not None:
                finish_reason = chunk.finish_reason
            if chunk.usage:
                usage = dict(chunk.usage)
            if chunk.raw_response:
                raw_response = dict(chunk.raw_response)

            if chunk.tool_calls:
                current_tool_call_key = _tool_call_state_key(tool_calls)
                if current_tool_call_key != tool_call_state_key:
                    tool_call_state_key = current_tool_call_key
                    yield emit_event(
                        "assistant.tool_call.delta",
                        model=model,
                        provider_id=provider_id,
                        iteration=iteration,
                        retry_count=retry_count,
                        content=content,
                        tool_calls=list(tool_calls),
                        finish_reason=finish_reason,
                    )

            if chunk.event == "delta" and chunk.delta:
                yield emit_event(
                    "assistant.delta",
                    model=model,
                    provider_id=provider_id,
                    iteration=iteration,
                    retry_count=retry_count,
                    delta=chunk.delta,
                    content=content,
                    tool_calls=list(tool_calls),
                    finish_reason=finish_reason,
                )

        if not saw_chunk:
            with bind_session_context(session_id):
                return self._llm_executor(request, self._root), False

        return (
            LLMChatResponse(
                model=model,
                provider_id=provider_id,
                content=content,
                tool_calls=list(tool_calls),
                finish_reason=finish_reason,
                usage=usage,
                raw_response=raw_response,
            ),
            emitted_text_deltas,
        )

    def _persist_session(
        self,
        session_id: str,
        model: str,
        messages: list[ChatMessage],
        existing_session,
    ) -> None:
        self._session_store.save(
            session_id=session_id,
            model=model,
            messages=messages,
            created_at=existing_session.created_at if existing_session is not None else None,
        )


def create_meta_harness_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_function(
        "formal_analysis",
        _run_formal_analysis,
        description="Run MetaFramework.execute() and return the formal analysis result.",
        parameters={
            "type": "object",
            "properties": {
                "problem_statement": {"type": "string"},
                "domain_hints": {"type": "array", "items": {"type": "string"}},
                "data_refs": {"type": "array", "items": {"type": "string"}},
                "data": {"type": "object"},
                "params": {"type": "object"},
                "objectives": {"type": "array", "items": {"type": "string"}},
                "allowed_methods": {"type": "array", "items": {"type": "string"}},
                "target_evidence_grade": {"type": "string"},
                "target_sr_grade": {"type": "string"},
                "meta_routing": {"type": "object"},
            },
            "required": ["problem_statement"],
        },
    )
    registry.register_function(
        "web_search",
        run_web_search_tool,
        description="Network-grounded shallow search (instant-answer JSON). Returns results[] and citations[] for the desktop evidence pane.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    )
    return registry


def _run_formal_analysis(arguments: dict[str, Any]) -> dict[str, Any]:
    problem_statement = str(arguments.get("problem_statement", "")).strip()
    if not problem_statement:
        raise ValueError("formal_analysis requires 'problem_statement'.")

    request = MetaAnalysisRequest(
        problem_statement=problem_statement,
        domain_hints=_string_list(arguments.get("domain_hints")),
        data_refs=_string_list(arguments.get("data_refs")),
        data=_mapping(arguments.get("data")),
        params=_mapping(arguments.get("params")),
        objectives=_string_list(arguments.get("objectives")),
        allowed_methods=_string_list(arguments.get("allowed_methods")),
        target_evidence_grade=str(arguments.get("target_evidence_grade", "CE-C1") or "CE-C1"),
        target_sr_grade=str(arguments.get("target_sr_grade", "") or "").strip(),
        meta_routing=_mapping(arguments.get("meta_routing")),
    )
    return asdict(MetaFramework().execute(request))


def _resolve_loop_tools(request: ChatCompletionRequest, registry: ToolRegistry) -> list[ToolDefinition]:
    if not request.tools:
        return registry.list_definitions()

    tools = list(request.tools)
    for tool in tools:
        if not registry.has_tool(tool.name):
            raise ValueError(f"Agent loop tool '{tool.name}' is not registered.")
    return tools


def _normalize_chat_message(message: ChatMessage) -> ChatMessage:
    return ChatMessage(
        role=message.role,
        content=message.content,
        tool_call_id=message.tool_call_id,
        tool_calls=list(message.tool_calls),
    )


def _to_llm_message(message: ChatMessage) -> LLMMessage:
    return LLMMessage(
        role=message.role,
        content=message.content,
        tool_call_id=message.tool_call_id,
        tool_calls=list(message.tool_calls),
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return dict(value)


def _should_retry_empty_response(response: LLMChatResponse) -> bool:
    if response.tool_calls:
        return False
    return not response.content.strip()


def _build_empty_response_recovery_message(*, retry_count: int, retry_budget: int) -> ChatMessage:
    return ChatMessage(
        role="system",
        content=(
            "Recovery note: The previous assistant response was empty. "
            f"This is guided recovery attempt {retry_count} of {retry_budget}. "
            "Reflect briefly on why the reply was incomplete, then provide a concise direct answer or request a tool only if it is truly needed."
        ),
    )


def _build_tool_error_recovery_message(
    tool_results: list[ToolCallResult],
    *,
    retry_count: int,
    retry_budget: int,
) -> ChatMessage | None:
    if not tool_results or not all(result.is_error for result in tool_results):
        return None

    failures = "; ".join(_summarize_tool_error(result) for result in tool_results)
    return ChatMessage(
        role="system",
        content=(
            "Recovery note: The previous tool attempt failed. "
            f"This is guided recovery attempt {retry_count} of {retry_budget}. "
            f"Observed failures: {failures}. "
            "Reflect briefly on the failure, do not repeat the same failing tool call with the same "
            "arguments, and either fix the arguments, choose a different tool, or answer directly if no "
            "tool is required."
        ),
    )


def _summarize_tool_error(result: ToolCallResult) -> str:
    error = result.structured_content.get("error") if isinstance(result.structured_content, dict) else None
    if isinstance(error, dict):
        code = str(error.get("code", "")).strip()
        message = str(error.get("message", "")).strip() or result.content.strip()
    else:
        code = ""
        message = result.content.strip()

    summary = result.name or "tool"
    if code:
        summary = f"{summary} ({code})"
    if message:
        summary = f"{summary}: {message}"
    return summary


def _stream_error_message(chunk: LLMChatChunk) -> str:
    if isinstance(chunk.error, dict):
        message = chunk.error.get("message")
        if isinstance(message, str) and message:
            return message
        nested_error = chunk.error.get("error")
        if isinstance(nested_error, dict):
            nested_message = nested_error.get("message")
            if isinstance(nested_message, str) and nested_message:
                return nested_message
    return "Streaming LLM request failed."


def _tool_call_state_key(tool_calls: list[Any]) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        (
            str(getattr(call, "id", "") or ""),
            str(getattr(call, "type", "") or ""),
            str(getattr(call, "name", "") or ""),
            str(getattr(call, "arguments", "") or ""),
        )
        for call in tool_calls
    )


def _has_formal_analysis_call(tool_results: list[ToolCallResult]) -> bool:
    return any(result.name == "formal_analysis" for result in tool_results)


def _json_escape(value: str) -> str:
    import json

    return json.dumps(value)


__all__ = ["AgentLoop", "AgentLoopResult", "LLMExecutor", "LLMStreamExecutor", "create_meta_harness_tool_registry"]
