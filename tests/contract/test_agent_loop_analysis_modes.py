"""Contract tests for AgentLoop analysis_mode support."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pytest

from pyc_hermes_agent.contracts import (
    AgentLoopEvent,
    AgentLoopRequest,
    ChatCompletionRequest,
    ChatMessage,
)
from pyc_hermes_agent.hermes_engine.agent_loop import AgentLoop
from pyc_hermes_agent.llm_gateway import LLMChatRequest, LLMChatResponse


def _make_echo_executor(response_content: str = "Hello."):
    """Return a fake LLM executor that echoes a fixed response."""

    def executor(request: LLMChatRequest, root: Path) -> LLMChatResponse:
        return LLMChatResponse(
            model=request.model or "test-model",
            provider_id="test",
            content=response_content,
            finish_reason="stop",
        )

    return executor


def _collect_events(loop: AgentLoop, request: ChatCompletionRequest, **kwargs) -> list[AgentLoopEvent]:
    return list(loop.stream(request, **kwargs))


class TestAnalysisModeCasual:
    """Casual mode should behave identically to the default."""

    def test_casual_mode_default(self, tmp_path: Path):
        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=_make_echo_executor())
        request = ChatCompletionRequest(messages=[ChatMessage(content="hi")])
        result = loop.run(request, analysis_mode="casual")
        assert result.content == "Hello."

    def test_casual_mode_start_event_payload(self, tmp_path: Path):
        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=_make_echo_executor())
        request = ChatCompletionRequest(messages=[ChatMessage(content="hi")])
        events = _collect_events(loop, request, analysis_mode="casual")
        start_event = next(e for e in events if e.event == "start")
        assert start_event.payload["analysis_mode"] == "casual"


class TestAnalysisModeStructured:
    """Structured mode should inject a system message instructing structured output."""

    def test_structured_mode_injects_system_message(self, tmp_path: Path):
        captured_requests: list[LLMChatRequest] = []

        def capturing_executor(request: LLMChatRequest, root: Path) -> LLMChatResponse:
            captured_requests.append(request)
            return LLMChatResponse(
                model="test-model", provider_id="test",
                content="## Summary\nDone.", finish_reason="stop",
            )

        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=capturing_executor)
        request = ChatCompletionRequest(messages=[ChatMessage(content="analyze this")])
        loop.run(request, analysis_mode="structured")

        assert len(captured_requests) == 1
        llm_messages = captured_requests[0].messages
        system_contents = [m.content for m in llm_messages if m.role == "system"]
        assert any("## Summary" in c for c in system_contents)

    def test_structured_mode_start_event(self, tmp_path: Path):
        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=_make_echo_executor())
        request = ChatCompletionRequest(messages=[ChatMessage(content="hi")])
        events = _collect_events(loop, request, analysis_mode="structured")
        start_event = next(e for e in events if e.event == "start")
        assert start_event.payload["analysis_mode"] == "structured"


class TestAnalysisModeFormal:
    """Formal mode should auto-inject formal_analysis tool call when LLM doesn't call it."""

    def test_formal_mode_auto_injects_tool(self, tmp_path: Path):
        call_count = 0

        def counting_executor(request: LLMChatRequest, root: Path) -> LLMChatResponse:
            nonlocal call_count
            call_count += 1
            return LLMChatResponse(
                model="test-model", provider_id="test",
                content=f"Response {call_count}", finish_reason="stop",
            )

        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=counting_executor)
        request = ChatCompletionRequest(messages=[ChatMessage(content="analyze")])
        # With formal mode and max_iterations=3, the loop should:
        # 1. LLM responds without tool call -> auto-inject formal_analysis -> continue
        # 2. LLM responds incorporating tool result -> done
        result = loop.run(request, analysis_mode="formal", max_iterations=3)
        assert call_count == 2
        assert result.content == "Response 2"

    def test_formal_mode_emits_tool_result_event(self, tmp_path: Path):
        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=_make_echo_executor())
        request = ChatCompletionRequest(messages=[ChatMessage(content="analyze")])
        events = _collect_events(loop, request, analysis_mode="formal", max_iterations=3)
        tool_events = [e for e in events if e.event == "tool.result"]
        assert len(tool_events) >= 1
        assert tool_events[0].payload.get("auto_injected") is True


class TestAnalysisModeValidation:
    """Invalid analysis_mode should raise ValueError."""

    def test_invalid_mode_raises(self, tmp_path: Path):
        loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=_make_echo_executor())
        request = ChatCompletionRequest(messages=[ChatMessage(content="hi")])
        with pytest.raises(ValueError, match="Invalid analysis_mode"):
            loop.run(request, analysis_mode="invalid")


class TestAgentLoopRequestField:
    """The analysis_mode field on AgentLoopRequest defaults to 'casual'."""

    def test_default_value(self):
        req = AgentLoopRequest()
        assert req.analysis_mode == "casual"

    def test_explicit_value(self):
        req = AgentLoopRequest(analysis_mode="formal")
        assert req.analysis_mode == "formal"
