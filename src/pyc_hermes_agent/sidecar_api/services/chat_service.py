"""Chat and agent loop service functions."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Dict, TypedDict
from uuid import uuid4

from pyc_hermes_agent.contracts import (
    AgentLoopEvent,
    AgentLoopRequest,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResult,
    MetaAnalysisRequest,
)
from pyc_hermes_agent.hermes_engine import AgentLoop
from pyc_hermes_agent.llm_gateway import (
    execute_chat,
    LLMChatRequest,
    LLMMessage,
    resolve_opencode_like_config,
    stream_chat,
)
from pyc_hermes_agent.meta_harness import MetaFramework
from pyc_hermes_agent.sidecar_api.error_domains import DOMAIN_AGENT, DOMAIN_LLM
from pyc_hermes_agent.sidecar_api.services._normalize import (
    normalize_agent_loop_request,
    normalize_chat_request,
)
from pyc_hermes_agent.sidecar_api.services.common import (
    _error,
    _repo_root,
    _serialize,
    log_event,
    make_error_response,
)


class _AgentLoopRunKwargs(TypedDict, total=False):
    max_iterations: int
    session_id: str | None
    activated_skills: list[str]
    planning_enabled: bool
    retry_budget: int
    analysis_mode: str


def _to_llm_messages(request: ChatCompletionRequest) -> list:
    return [
        LLMMessage(
            role=m.role,
            content=m.content,
            tool_call_id=m.tool_call_id,
            tool_calls=list(m.tool_calls),
        )
        for m in request.messages
    ]


def invoke_chat_completion(request: ChatCompletionRequest, root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    try:
        nr = normalize_chat_request(request)
        model_id = nr.model or resolve_opencode_like_config(base).default_model
        log_event("llm.chat.started", model=model_id)
        result = execute_chat(
            LLMChatRequest(
                model=nr.model,
                messages=_to_llm_messages(nr),
                tools=nr.tools,
                temperature=nr.temperature,
                max_tokens=nr.max_tokens,
                timeout_seconds=nr.timeout_seconds,
                retry_attempts=nr.retry_attempts,
            ),
            base,
        )
        log_event(
            "llm.chat.finished",
            model=result.model,
            provider_id=result.provider_id,
            finish_reason=result.finish_reason or "unknown",
        )
        return _serialize(
            ChatCompletionResult(
                model=result.model,
                provider_id=result.provider_id,
                content=result.content,
                tool_calls=result.tool_calls,
                finish_reason=result.finish_reason,
                usage=result.usage,
                raw_response=result.raw_response,
            )
        )
    except Exception as exc:
        log_event("llm.chat.failed", error=str(exc))
        return make_error_response(
            "LLM_CHAT_FAILED", "provider", str(exc),
            domain=DOMAIN_LLM, retryable=True, degraded=False,
        )


def stream_chat_completion(request: ChatCompletionRequest, root: Path | None = None) -> Iterator[Dict[str, Any]]:
    base = root or _repo_root()
    nr = normalize_chat_request(request)
    model_id = nr.model or resolve_opencode_like_config(base).default_model
    log_event("llm.chat.stream.started", model=model_id)
    try:
        for chunk in stream_chat(
            LLMChatRequest(
                model=nr.model,
                messages=_to_llm_messages(nr),
                tools=nr.tools,
                temperature=nr.temperature,
                max_tokens=nr.max_tokens,
                timeout_seconds=nr.timeout_seconds,
                retry_attempts=nr.retry_attempts,
            ),
            base,
        ):
            payload = _serialize(
                ChatCompletionChunk(
                    event=chunk.event,
                    model=chunk.model,
                    provider_id=chunk.provider_id,
                    delta=chunk.delta,
                    content=chunk.content,
                    tool_calls=chunk.tool_calls,
                    finish_reason=chunk.finish_reason,
                    usage=chunk.usage,
                    error=chunk.error,
                    raw_response=chunk.raw_response,
                )
            )
            if chunk.event == "done":
                log_event(
                    "llm.chat.stream.finished",
                    model=chunk.model,
                    provider_id=chunk.provider_id,
                    finish_reason=chunk.finish_reason or "unknown",
                )
            yield payload
    except Exception as exc:
        log_event("llm.chat.stream.failed", error=str(exc))
        yield _serialize(
            ChatCompletionChunk(
                event="error", model=model_id, provider_id="",
                error=_error(
                    "LLM_CHAT_STREAM_FAILED", "provider", str(exc),
                    domain=DOMAIN_LLM, retryable=True, degraded=False,
                ),
            )
        )


def _build_analysis_card(problem_statement: str) -> Dict[str, Any] | None:
    """Run MetaFramework.execute() and return an analysis_card dict, or None on failure."""
    try:
        fw = MetaFramework()
        request = MetaAnalysisRequest(problem_statement=problem_statement)
        result = fw.execute(request)
        return {
            "method": result.selected_method,
            "evidence_grade": result.evidence_grade,
            "sr_grade": result.sr_grade,
            "risks": list(result.risks),
            "assumptions": list(result.assumptions),
            "rationale": result.method_rationale,
            "degraded": result.degraded,
        }
    except Exception as exc:
        log_event("analysis_card.failed", error=str(exc))
        return None


def _build_run_kwargs(nr: AgentLoopRequest) -> _AgentLoopRunKwargs:
    run_kwargs: _AgentLoopRunKwargs = {
        "max_iterations": nr.max_iterations,
        "session_id": nr.session_id,
    }
    if nr.activated_skills:
        run_kwargs["activated_skills"] = nr.activated_skills
    if nr.planning_enabled is False:
        run_kwargs["planning_enabled"] = False
    if nr.retry_budget != 1:
        run_kwargs["retry_budget"] = nr.retry_budget
    if nr.analysis_mode != "casual":
        run_kwargs["analysis_mode"] = nr.analysis_mode
    return run_kwargs


def _agent_chat_request(nr: AgentLoopRequest) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model=nr.model,
        messages=nr.messages,
        tools=nr.tools,
        temperature=nr.temperature,
        max_tokens=nr.max_tokens,
        timeout_seconds=nr.timeout_seconds,
        retry_attempts=nr.retry_attempts,
    )


def _extract_last_user_message(nr: AgentLoopRequest) -> str:
    """Extract the last user message content for formal analysis."""
    for msg in reversed(nr.messages):
        if msg.role == "user":
            return msg.content
    return ""


def run_agent_loop(request: AgentLoopRequest, root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    try:
        nr = normalize_agent_loop_request(request)
        model_id = nr.model or resolve_opencode_like_config(base).default_model
        log_event("agent.loop.started", model=model_id, max_iterations=nr.max_iterations)
        result = AgentLoop(root=base).run(_agent_chat_request(nr), **_build_run_kwargs(nr))
        log_event(
            "agent.loop.finished",
            model=result.model,
            provider_id=result.provider_id,
            finish_reason=result.finish_reason or "unknown",
            iterations=result.iterations,
        )
        serialized = _serialize(result)
        if nr.analysis_mode == "formal":
            problem = _extract_last_user_message(nr)
            card = _build_analysis_card(problem)
            if card:
                serialized["analysis_card"] = card
        return serialized
    except Exception as exc:
        log_event("agent.loop.failed", error=str(exc))
        return make_error_response(
            "AGENT_LOOP_FAILED", "runtime", str(exc),
            domain=DOMAIN_AGENT, retryable=False, degraded=False,
        )


def stream_agent_loop(request: AgentLoopRequest, root: Path | None = None) -> Iterator[Dict[str, Any]]:
    base = root or _repo_root()
    nr = normalize_agent_loop_request(request)
    model_id = nr.model or resolve_opencode_like_config(base).default_model
    log_event("agent.loop.stream.started", model=model_id, max_iterations=nr.max_iterations)
    run_kwargs = _build_run_kwargs(nr)

    try:
        for event in AgentLoop(root=base).stream(_agent_chat_request(nr), **run_kwargs):
            payload = _serialize(event)
            if event.event == "done":
                log_event(
                    "agent.loop.stream.finished",
                    model=event.model, provider_id=event.provider_id,
                    finish_reason=event.finish_reason or "unknown",
                    iterations=event.iteration, trace_id=event.trace_id, sequence=event.sequence,
                )
                if nr.analysis_mode == "formal":
                    problem = _extract_last_user_message(nr)
                    card = _build_analysis_card(problem)
                    if card:
                        payload["analysis_card"] = card
            elif event.event == "error":
                log_event(
                    "agent.loop.stream.failed",
                    error=event.error.get("message", "unknown"),
                    trace_id=event.trace_id, sequence=event.sequence,
                )
            yield payload
    except Exception as exc:
        fallback_event = AgentLoopEvent(
            trace_id=str(uuid4()), sequence=1, event="error", is_terminal=True,
            session_id=nr.session_id, model=model_id,
            error=_error(
                "AGENT_LOOP_STREAM_FAILED", "runtime", str(exc),
                domain=DOMAIN_AGENT, retryable=False, degraded=False,
            ),
        )
        log_event(
            "agent.loop.stream.failed", error=str(exc),
            trace_id=fallback_event.trace_id, sequence=fallback_event.sequence,
        )
        yield _serialize(fallback_event)
