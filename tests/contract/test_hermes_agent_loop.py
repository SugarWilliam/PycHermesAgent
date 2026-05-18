from pathlib import Path

from pyc_hermes_agent.contracts import ChatCompletionRequest, ChatMessage, ToolCall
from pyc_hermes_agent.hermes_engine import AgentLoop, AgentSessionStore, ToolRegistry, create_meta_harness_tool_registry, get_current_session_id
from pyc_hermes_agent.llm_gateway import LLMChatChunk, LLMChatResponse


def test_agent_loop_runs_tool_call_roundtrip(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register_function("echo_text", lambda args: {"echo": args["text"]})
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        if len(calls) == 1:
            assert request.tools[0].name == "echo_text"
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="",
                finish_reason="tool_calls",
                tool_calls=[ToolCall(id="call-1", name="echo_text", arguments='{"text": "hello"}')],
            )

        assert len(request.messages) == 3
        assert request.messages[1].role == "assistant"
        assert request.messages[1].tool_calls[0].name == "echo_text"
        assert request.messages[2].role == "tool"
        assert request.messages[2].tool_call_id == "call-1"
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Echoed hello.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor, tool_registry=registry)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Echo hello")],
        )
    )

    assert result.iterations == 2
    assert result.session_id
    assert result.plan is None
    assert result.content == "Echoed hello."
    assert len(result.tool_results) == 1
    assert result.tool_results[0].structured_content == {"echo": "hello"}
    assert [message.role for message in result.messages] == ["user", "assistant", "tool", "assistant"]


def test_agent_loop_uses_builtin_formal_analysis_tool(tmp_path: Path) -> None:
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        if len(calls) == 1:
            assert any(tool.name == "formal_analysis" for tool in request.tools)
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="",
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        id="call-formal-analysis",
                        name="formal_analysis",
                        arguments=(
                            '{"problem_statement": "network pagerank analysis", '
                            '"data": {"adjacency": [[0.0, 1.0], [1.0, 0.0]]}, '
                            '"params": {"analysis": "pagerank"}}'
                        ),
                    )
                ],
            )

        assert request.messages[0].role == "system"
        assert request.messages[0].content.startswith("Execution plan:")
        assert request.messages[-2].role == "assistant"
        assert request.messages[-2].tool_calls[0].name == "formal_analysis"
        assert request.messages[-1].role == "tool"
        assert "A-22" in request.messages[-1].content
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Completed formal analysis.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Run formal analysis")],
        )
    )

    assert result.iterations == 2
    assert result.session_id
    assert result.plan is not None
    assert any(step.kind == "tool" for step in result.plan.steps)
    assert result.content == "Completed formal analysis."
    assert result.tool_results[0].structured_content["selected_method"] == "A-22"


def test_meta_harness_tool_registry_exposes_formal_analysis() -> None:
    registry = create_meta_harness_tool_registry()

    assert registry.has_tool("formal_analysis") is True
    descriptor = registry.list_descriptors()[0]
    assert descriptor.name == "formal_analysis"


def test_agent_loop_rejects_unknown_requested_tool(tmp_path: Path) -> None:
    loop = AgentLoop(root=tmp_path, llm_executor=lambda request, root: LLMChatResponse())

    try:
        loop.run(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Hello")],
                tools=[],
            ),
            tool_registry=ToolRegistry(),
        )
    except ValueError as exc:
        assert False, f"Unexpected error: {exc}"


def test_agent_loop_persists_and_resumes_session_history(tmp_path: Path) -> None:
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        if len(calls) == 1:
            assert len(request.messages) == 1
            assert request.messages[0].content == "First turn"
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="First reply.",
                finish_reason="stop",
            )

        assert len(request.messages) == 3
        assert request.messages[0].content == "First turn"
        assert request.messages[1].content == "First reply."
        assert request.messages[2].content == "Second turn"
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Second reply.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=fake_llm_executor)
    first = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="First turn")],
        )
    )
    second = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Second turn")],
        ),
        session_id=first.session_id,
    )

    store = AgentSessionStore(root=tmp_path)
    saved = store.load(first.session_id)

    assert first.session_id == second.session_id
    assert saved is not None
    assert [message.content for message in saved.messages] == ["First turn", "First reply.", "Second turn", "Second reply."]


def test_agent_loop_persists_partial_history_on_failure(tmp_path: Path) -> None:
    def fake_llm_executor(request, _root):
        raise RuntimeError("boom")

    loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=fake_llm_executor)

    try:
        loop.run(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Hello")],
            ),
            session_id="session-failure",
        )
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        assert False, "Expected RuntimeError"

    saved = AgentSessionStore(root=tmp_path).load("session-failure")

    assert saved is not None
    assert [message.content for message in saved.messages] == ["Hello"]


def test_agent_loop_injects_session_memory_into_prompt(tmp_path: Path) -> None:
    store = AgentSessionStore(root=tmp_path)
    store.save(
        session_id="session-memory",
        model="openai-compatible/demo-model",
        messages=[
            ChatMessage(role="user", content="Preference one"),
            ChatMessage(role="assistant", content="Acknowledged one"),
            ChatMessage(role="user", content="Preference two"),
            ChatMessage(role="assistant", content="Acknowledged two"),
            ChatMessage(role="user", content="Preference three"),
            ChatMessage(role="assistant", content="Acknowledged three"),
            ChatMessage(role="user", content="Preference four"),
            ChatMessage(role="assistant", content="Acknowledged four"),
            ChatMessage(role="user", content="Preference five"),
            ChatMessage(role="assistant", content="Acknowledged five"),
        ],
    )
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        assert request.messages[0].role == "system"
        assert request.messages[0].content.startswith("<memory-context>Session memory:")
        assert "Preference one" in request.messages[0].content
        raw_contents = [message.content for message in request.messages[1:]]
        assert "Preference one" not in raw_contents
        assert raw_contents[-1] == "New turn"
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Reply with memory.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=fake_llm_executor, session_store=store)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="New turn")],
        ),
        session_id="session-memory",
    )

    assert len(calls) == 1
    assert result.content == "Reply with memory."


def test_agent_loop_sanitizes_nested_memory_tags(tmp_path: Path) -> None:
    store = AgentSessionStore(root=tmp_path)
    store.save(
        session_id="session-sanitize",
        model="openai-compatible/demo-model",
        messages=[
            ChatMessage(role="user", content="<memory-context>nested</memory-context> context"),
            ChatMessage(role="assistant", content="Ack"),
            ChatMessage(role="user", content="Need follow up"),
            ChatMessage(role="assistant", content="Working"),
            ChatMessage(role="user", content="Keep style concise"),
            ChatMessage(role="assistant", content="Understood"),
            ChatMessage(role="user", content="Track TODOs"),
            ChatMessage(role="assistant", content="Tracking"),
            ChatMessage(role="user", content="Use tests"),
            ChatMessage(role="assistant", content="Will do"),
        ],
    )

    def fake_llm_executor(request, _root):
        memory_message = request.messages[0]
        assert memory_message.role == "system"
        assert memory_message.content.count("<memory-context>") == 1
        assert memory_message.content.count("</memory-context>") == 1
        assert "nested context" in memory_message.content
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Reply.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=fake_llm_executor, session_store=store)
    loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Continue")],
        ),
        session_id="session-sanitize",
    )


def test_agent_loop_binds_explicit_skill_context(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".opencode" / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: demo-skill
description: Demo skill instructions
---

# Demo Skill

Use this skill only when explicitly activated.
""",
        encoding="utf-8",
    )
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        assert request.messages[0].role == "system"
        assert "<skill-context>" in request.messages[0].content
        assert "Active skill: demo-skill" in request.messages[0].content
        assert "Use this skill only when explicitly activated." in request.messages[0].content
        assert "Script execution is disabled" in request.messages[0].content
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Skill-bound reply.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Use the skill")],
        ),
        activated_skills=["demo-skill"],
    )

    assert len(calls) == 1
    assert result.content == "Skill-bound reply."


def test_agent_loop_start_event_records_skill_activation_audit_metadata(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".opencode" / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: demo-skill
description: Demo
---

Skill body
""",
        encoding="utf-8",
    )

    def fake_llm_executor(request, _root):
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="ok",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor)
    events = list(
        loop.stream(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="hi")],
            ),
            activated_skills=["demo-skill"],
        )
    )
    start = events[0]
    assert start.event == "start"
    assert start.payload["activated_skills"] == ["demo-skill"]
    policy = start.payload["skills_runtime_policy"]
    assert policy["activation_mode"] == "explicit_only"
    assert policy["script_execution"] == "disabled"
    assert policy["policy_id"] == "skill-runtime-permissions-phase1-v0.2.0"


def test_agent_loop_start_event_lists_empty_activated_skills_by_default(tmp_path: Path) -> None:
    def fake_llm_executor(request, _root):
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="ok",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor)
    events = list(
        loop.stream(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="hi")],
            ),
        )
    )
    assert events[0].payload["activated_skills"] == []


def test_agent_loop_rejects_unknown_activated_skill(tmp_path: Path) -> None:
    loop = AgentLoop(root=tmp_path, llm_executor=lambda request, root: LLMChatResponse())

    try:
        loop.run(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Use missing skill")],
            ),
            activated_skills=["missing-skill"],
        )
    except ValueError as exc:
        assert "Unknown activated skill" in str(exc)
    else:
        assert False, "Expected unknown skill activation to fail"


def test_agent_loop_injects_execution_plan_into_prompt(tmp_path: Path) -> None:
    def fake_llm_executor(request, _root):
        assert request.messages[0].role == "system"
        assert request.messages[0].content.startswith("Execution plan:")
        assert "formal_analysis" in request.messages[0].content
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Planned response.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=fake_llm_executor)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Run formal analysis for this problem")],
        )
    )

    assert result.plan is not None
    assert result.plan.summary
    assert any(step.kind == "tool" for step in result.plan.steps)


def test_agent_loop_retries_after_empty_response(tmp_path: Path) -> None:
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        if len(calls) == 1:
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="",
                finish_reason="stop",
            )

        assert request.messages[0].role == "system"
        assert request.messages[0].content.startswith("Recovery note: The previous assistant response was empty.")
        assert request.messages[-1].content == "Say hello"
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Hello.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Say hello")],
        ),
        planning_enabled=False,
        retry_budget=1,
    )

    assert len(calls) == 2
    assert result.content == "Hello."
    assert result.retry_count == 1
    assert [message.role for message in result.messages] == ["user", "assistant"]


def test_agent_loop_retries_after_tool_failure_with_reflection_hint(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register_function("always_fails", lambda args: (_ for _ in ()).throw(RuntimeError("boom")))
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        if len(calls) == 1:
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="",
                finish_reason="tool_calls",
                tool_calls=[ToolCall(id="call-1", name="always_fails", arguments='{"text": "hello"}')],
            )

        assert request.messages[0].role == "system"
        assert request.messages[0].content.startswith("Recovery note: The previous tool attempt failed.")
        assert "always_fails" in request.messages[0].content
        assert request.messages[-2].role == "assistant"
        assert request.messages[-1].role == "tool"
        assert request.messages[-1].content == "boom"
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="I could not complete the tool call, so here is a direct answer.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor, tool_registry=registry)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Try the tool")],
        ),
        planning_enabled=False,
        retry_budget=1,
    )

    assert len(calls) == 2
    assert result.retry_count == 1
    assert len(result.tool_results) == 1
    assert result.tool_results[0].is_error is True
    assert result.content == "I could not complete the tool call, so here is a direct answer."


def test_agent_loop_binds_session_context_for_sync_llm_and_tool_dispatch(tmp_path: Path) -> None:
    registry = ToolRegistry()
    observed_llm_sessions = []
    observed_tool_sessions = []

    def echo_handler(args):
        observed_tool_sessions.append(get_current_session_id())
        return {"echo": args["text"]}

    registry.register_function("echo_text", echo_handler)

    def fake_llm_executor(request, _root):
        observed_llm_sessions.append(get_current_session_id())
        if len(observed_llm_sessions) == 1:
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="",
                finish_reason="tool_calls",
                tool_calls=[ToolCall(id="call-1", name="echo_text", arguments='{"text": "hello"}')],
            )
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Echoed hello.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor, tool_registry=registry)
    result = loop.run(
        ChatCompletionRequest(
            model="openai-compatible/demo-model",
            messages=[ChatMessage(role="user", content="Echo hello")],
        ),
        session_id="session-context",
        planning_enabled=False,
    )

    assert result.content == "Echoed hello."
    assert observed_llm_sessions == ["session-context", "session-context"]
    assert observed_tool_sessions == ["session-context"]
    assert get_current_session_id() is None


def test_agent_loop_stream_emits_events_for_tool_roundtrip(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register_function("echo_text", lambda args: {"echo": args["text"]})
    calls = []

    def fake_llm_executor(request, _root):
        calls.append(request)
        if len(calls) == 1:
            return LLMChatResponse(
                model="openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="",
                finish_reason="tool_calls",
                tool_calls=[ToolCall(id="call-1", name="echo_text", arguments='{"text": "hello"}')],
            )
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Echoed hello.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor, tool_registry=registry)
    events = list(
        loop.stream(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Echo hello")],
            ),
            planning_enabled=False,
        )
    )

    assert events[0].event == "start"
    assert any(event.event == "assistant.completed" and event.tool_calls for event in events)
    assert any(event.event == "tool.result" for event in events)
    assert events[-1].event == "done"
    assert events[-1].is_terminal is True
    assert events[-1].payload["result"].content == "Echoed hello."
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert len({event.trace_id for event in events}) == 1
    assert all(bool(event.event_id) for event in events)


def test_agent_loop_stream_emits_token_level_assistant_deltas(tmp_path: Path) -> None:
    def fake_llm_executor(request, _root):
        raise AssertionError("Synchronous executor should not be used for token streaming test.")

    def fake_llm_stream_executor(request, _root):
        assert request.messages[-1].content == "Say hello"
        yield LLMChatChunk(
            event="delta",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            delta="Hello",
            content="Hello",
        )
        yield LLMChatChunk(
            event="delta",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            delta=" world",
            content="Hello world",
            finish_reason="stop",
        )
        yield LLMChatChunk(
            event="done",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Hello world",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor, llm_stream_executor=fake_llm_stream_executor)
    events = list(
        loop.stream(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Say hello")],
            ),
            planning_enabled=False,
        )
    )

    delta_events = [event for event in events if event.event == "assistant.delta"]
    assert [event.delta for event in delta_events] == ["Hello", " world"]
    assert delta_events[-1].content == "Hello world"
    assert events[-2].event == "assistant.completed"
    assert events[-2].content == "Hello world"
    assert events[-1].event == "done"
    assert events[-1].payload["result"].content == "Hello world"


def test_agent_loop_stream_binds_session_context_for_streaming_llm(tmp_path: Path) -> None:
    observed_stream_sessions = []

    def fake_llm_executor(request, _root):
        raise AssertionError("Synchronous executor should not be used for streaming session-context test.")

    def fake_llm_stream_executor(request, _root):
        observed_stream_sessions.append(get_current_session_id())
        yield LLMChatChunk(
            event="delta",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            delta="Hello",
            content="Hello",
        )
        observed_stream_sessions.append(get_current_session_id())
        yield LLMChatChunk(
            event="done",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Hello",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, llm_executor=fake_llm_executor, llm_stream_executor=fake_llm_stream_executor)
    events = list(
        loop.stream(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Say hello")],
            ),
            session_id="stream-session",
            planning_enabled=False,
        )
    )

    assert observed_stream_sessions == ["stream-session", "stream-session"]
    assert events[-1].event == "done"
    assert events[-1].payload["result"].content == "Hello"
    assert get_current_session_id() is None


def test_agent_loop_stream_emits_tool_call_delta_events(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register_function("echo_text", lambda args: {"echo": args["text"]})

    def fake_llm_executor(request, _root):
        raise AssertionError("Synchronous executor should not be used for tool-call delta streaming test.")

    def fake_llm_stream_executor(request, _root):
        yield LLMChatChunk(
            event="delta",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            tool_calls=[ToolCall(id="call-1", name="echo_text", arguments='{"text":"he')],
        )
        yield LLMChatChunk(
            event="delta",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            tool_calls=[ToolCall(id="call-1", name="echo_text", arguments='{"text":"hello"}')],
            finish_reason="tool_calls",
        )
        yield LLMChatChunk(
            event="done",
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            tool_calls=[ToolCall(id="call-1", name="echo_text", arguments='{"text":"hello"}')],
            finish_reason="tool_calls",
        )

    def fake_followup_executor(request, _root):
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Echoed hello.",
            finish_reason="stop",
        )

    stream_calls = {"count": 0}

    def switching_stream_executor(request, root):
        stream_calls["count"] += 1
        if stream_calls["count"] == 1:
            yield from fake_llm_stream_executor(request, root)
            return
        return
        yield

    sync_calls = {"count": 0}

    def switching_sync_executor(request, root):
        sync_calls["count"] += 1
        return fake_followup_executor(request, root)

    loop = AgentLoop(
        root=tmp_path,
        llm_executor=switching_sync_executor,
        llm_stream_executor=switching_stream_executor,
        tool_registry=registry,
    )
    events = list(
        loop.stream(
            ChatCompletionRequest(
                model="openai-compatible/demo-model",
                messages=[ChatMessage(role="user", content="Echo hello")],
            ),
            planning_enabled=False,
        )
    )

    tool_delta_events = [event for event in events if event.event == "assistant.tool_call.delta"]
    assert len(tool_delta_events) == 2
    assert tool_delta_events[0].tool_calls[0].arguments == '{"text":"he'
    assert tool_delta_events[1].tool_calls[0].arguments == '{"text":"hello"}'
    assert stream_calls["count"] == 2
    assert sync_calls["count"] == 1
    assert any(event.event == "tool.result" for event in events)
    assert events[-1].event == "done"
    assert events[-1].payload["result"].content == "Echoed hello."
