from pyc_hermes_agent import SidecarClient, SidecarHealthStatus
from pyc_hermes_agent.contracts import AgentLoopRequest, MetaAnalysisRequest, RetrievalRequest


def test_sidecar_client_runtime_paths_in_process(tmp_path) -> None:
    client = SidecarClient(root=tmp_path)
    snap = client.get_runtime_paths_snapshot()
    assert snap["logs_dir"]
    assert "mrag_core" in snap["mrag_dir"].replace("\\", "/")
    assert ".pyc_hermes_agent_runtime" in snap["config_dir"].replace("\\", "/")


def test_sidecar_client_reads_top_level_status_label_only() -> None:
    client = SidecarClient(
        health_fetcher=lambda _root: {
            "status_label": "ready-with-warnings",
            "degraded": False,
            "hermes": {"status_label": "unavailable"},
        }
    )

    status = client.get_health_status()

    assert status.status_label == "ready-with-warnings"
    assert status.degraded is False
    assert status.payload["hermes"]["status_label"] == "unavailable"


def test_sidecar_client_falls_back_to_degraded_when_status_label_missing() -> None:
    client = SidecarClient(
        health_fetcher=lambda _root: {
            "degraded": True,
            "hermes": {"status_label": "ready-with-warnings"},
        }
    )

    status = client.get_health_status()

    assert status.status_label == "degraded"
    assert status.degraded is True


def test_sidecar_client_falls_back_to_unavailable_without_top_level_status() -> None:
    client = SidecarClient(
        health_fetcher=lambda _root: {
            "degraded": False,
            "hermes": {"status_label": "ready-with-warnings"},
        }
    )

    status = client.get_health_status()

    assert status.status_label == "unavailable"
    assert status.degraded is False


def test_package_root_exports_sidecar_client() -> None:
    client = SidecarClient(
        health_fetcher=lambda _root: {
            "status_label": "ready",
            "degraded": False,
        }
    )

    status = client.get_health_status()

    assert isinstance(status, SidecarHealthStatus)
    assert status.status_label == "ready"


def test_sidecar_client_supports_core_in_process_api_calls(tmp_path) -> None:
    client = SidecarClient(root=tmp_path)

    config = client.get_config_snapshot()
    providers = client.list_providers()
    analysis = client.invoke_formal_analysis(
        MetaAnalysisRequest(
            problem_statement="network pagerank analysis",
            data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            params={"analysis": "pagerank"},
        )
    )
    kb = client.create_knowledge_base("client-in-process-kb")
    client.ingest_text_document(
        kb["knowledge_base_id"],
        "MetaHarness selects methods and MRAG packages evidence with citations.",
        title="In-process note",
    )
    result = client.search_knowledge_base(kb["knowledge_base_id"], RetrievalRequest(query="evidence citations", top_k=2))

    assert config["default_model"]
    assert any(provider["id"] == "github-copilot" for provider in providers)
    assert analysis["analysis"]["selected_method"] == "A-22"
    assert result["hits"]


def test_sidecar_client_supports_agent_loop_in_process(monkeypatch, tmp_path) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def run(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopResult

            assert planning_enabled is True
            assert retry_budget == 1
            return AgentLoopResult(
                session_id="session-1",
                model=request.model or "openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="Loop complete.",
                finish_reason="stop",
                iterations=1,
                retry_count=0,
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    client = SidecarClient(root=tmp_path)

    result = client.run_agent_loop(
        AgentLoopRequest(
            session_id="session-1",
            model="openai-compatible/demo-model",
            messages=[{"role": "user", "content": "Hello"}],
        )
    )

    assert result["session_id"] == "session-1"
    assert result["content"] == "Loop complete."
    assert result["iterations"] == 1


def test_sidecar_client_passes_retry_budget_in_process(monkeypatch, tmp_path) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def run(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopResult

            assert planning_enabled is False
            assert retry_budget == 2
            return AgentLoopResult(
                session_id="session-2",
                model=request.model or "openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="Retried.",
                finish_reason="stop",
                iterations=2,
                retry_count=1,
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    client = SidecarClient(root=tmp_path)

    result = client.run_agent_loop(
        AgentLoopRequest(
            session_id="session-2",
            model="openai-compatible/demo-model",
            messages=[{"role": "user", "content": "Hello"}],
            planning_enabled=False,
            retry_budget=2,
        )
    )

    assert result["session_id"] == "session-2"
    assert result["retry_count"] == 1


def test_sidecar_client_streams_agent_loop_in_process(monkeypatch, tmp_path) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopEvent, AgentLoopResult

            yield AgentLoopEvent(event_id="event-1", trace_id="trace-1", sequence=1, event="start", session_id=session_id or "session-1", model=request.model)
            yield AgentLoopEvent(
                event_id="event-2",
                trace_id="trace-1",
                sequence=2,
                event="assistant.tool_call.delta",
                session_id=session_id or "session-1",
                model=request.model,
                tool_calls=[{"id": "call-1", "name": "echo_text", "arguments": '{"text":"he'}],
            )
            yield AgentLoopEvent(
                event_id="event-3",
                trace_id="trace-1",
                sequence=3,
                event="assistant.delta",
                session_id=session_id or "session-1",
                model=request.model,
                delta="Hello",
            )
            yield AgentLoopEvent(
                event_id="event-4",
                trace_id="trace-1",
                sequence=4,
                event="done",
                is_terminal=True,
                session_id=session_id or "session-1",
                model=request.model,
                content="Hello",
                payload={"result": AgentLoopResult(session_id=session_id or "session-1", model=request.model, content="Hello")},
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    client = SidecarClient(root=tmp_path)

    events = list(
        client.stream_agent_loop(
            AgentLoopRequest(
                session_id="session-1",
                model="openai-compatible/demo-model",
                messages=[{"role": "user", "content": "Hello"}],
            )
        )
    )

    assert events[0]["event"] == "start"
    assert events[0]["trace_id"] == "trace-1"
    assert events[0]["sequence"] == 1
    assert events[1]["event"] == "assistant.tool_call.delta"
    assert events[1]["tool_calls"][0]["name"] == "echo_text"
    assert events[2]["event"] == "assistant.delta"
    assert events[-1]["event"] == "done"
    assert events[-1]["is_terminal"] is True
