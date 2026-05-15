import json
import threading
from urllib.request import Request, urlopen

from pyc_hermes_agent import SidecarClient
from pyc_hermes_agent.contracts import AgentLoopRequest, MetaAnalysisRequest, RetrievalRequest
from pyc_hermes_agent.sidecar_api import create_http_server

from .test_sidecar_api import _make_fake_hermes_checkout


def _start_server(*, root=None):
    server = create_http_server(port=0, root=root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _get_json(url: str) -> tuple[int, dict]:
    with urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _post_sse(url: str, payload: dict) -> tuple[int, list[dict]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        chunks: list[str] = []
        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if not line:
                continue
            if line.startswith("data:"):
                chunks.append(line[5:].lstrip())
        return response.status, [json.loads(chunk) for chunk in chunks]


def test_sidecar_http_server_serves_health_and_http_client(tmp_path) -> None:
    _make_fake_hermes_checkout(tmp_path)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload = _get_json(f"{base_url}/health")
        client_status = SidecarClient(base_url=base_url).get_health_status()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert payload["status_label"] == "ready-with-warnings"
    assert client_status.status_label == "ready-with-warnings"
    assert client_status.degraded is False


def test_sidecar_http_server_runs_formal_analysis(tmp_path) -> None:
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload = _post_json(
            f"{base_url}/formal-analysis",
            {
                "problem_statement": "network pagerank analysis",
                "data": {"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
                "params": {"analysis": "pagerank"},
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert payload["analysis"]["selected_method"] == "A-22"


def test_sidecar_http_server_runs_agent_loop(tmp_path, monkeypatch) -> None:
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
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload = _post_json(
            f"{base_url}/agent/run",
            {
                "session_id": "session-1",
                "model": "openai-compatible/demo-model",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert payload["session_id"] == "session-1"
    assert payload["content"] == "Loop complete."
    assert payload["iterations"] == 1
    assert payload["retry_count"] == 0


def test_sidecar_http_server_creates_and_searches_knowledge_bases(tmp_path) -> None:
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        create_status, knowledge_base = _post_json(f"{base_url}/knowledge-bases", {"name": "http-kb"})
        document_status, _document = _post_json(
            f"{base_url}/knowledge-bases/{knowledge_base['knowledge_base_id']}/documents/text",
            {
                "text": "MetaHarness selects methods and MRAG packages evidence with citations.",
                "title": "HTTP note",
            },
        )
        search_status, result = _post_json(
            f"{base_url}/knowledge-bases/{knowledge_base['knowledge_base_id']}/search",
            {"query": "evidence citations", "top_k": 2},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert create_status == 201
    assert document_status == 201
    assert search_status == 200
    assert result["hits"]
    assert result["citations"]


def test_sidecar_client_supports_core_http_api_calls(tmp_path) -> None:
    _make_fake_hermes_checkout(tmp_path)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    client = SidecarClient(base_url=base_url)

    try:
        config = client.get_config_snapshot()
        bridge_health = client.get_hermes_bridge_health()
        providers = client.list_providers()
        analysis = client.invoke_formal_analysis(
            MetaAnalysisRequest(
                problem_statement="network pagerank analysis",
                data={"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
                params={"analysis": "pagerank"},
            )
        )
        kb = client.create_knowledge_base("client-http-kb")
        client.ingest_text_document(
            kb["knowledge_base_id"],
            "MetaHarness selects methods and MRAG packages evidence with citations.",
            title="HTTP client note",
        )
        result = client.search_knowledge_base(kb["knowledge_base_id"], RetrievalRequest(query="evidence citations", top_k=2))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert config["default_model"]
    assert bridge_health["bridge_ready"] is True
    assert any(provider["id"] == "github-copilot" for provider in providers)
    assert analysis["analysis"]["selected_method"] == "A-22"
    assert result["hits"]


def test_sidecar_client_supports_agent_loop_over_http(tmp_path, monkeypatch) -> None:
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
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    client = SidecarClient(base_url=base_url)

    try:
        result = client.run_agent_loop(
            AgentLoopRequest(
                session_id="session-1",
                model="openai-compatible/demo-model",
                messages=[{"role": "user", "content": "Hello"}],
            )
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result["session_id"] == "session-1"
    assert result["content"] == "Loop complete."
    assert result["iterations"] == 1


def test_sidecar_http_server_passes_retry_budget_to_agent_loop(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def run(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopResult

            assert planning_enabled is False
            assert retry_budget == 2
            return AgentLoopResult(
                session_id=session_id or "session-2",
                model=request.model or "openai-compatible/demo-model",
                provider_id="openai-compatible",
                content="Retried.",
                finish_reason="stop",
                iterations=2,
                retry_count=1,
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload = _post_json(
            f"{base_url}/agent/run",
            {
                "session_id": "session-2",
                "model": "openai-compatible/demo-model",
                "messages": [{"role": "user", "content": "Hello"}],
                "planning_enabled": False,
                "retry_budget": 2,
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert payload["retry_count"] == 1


def test_sidecar_http_server_streams_agent_loop_events(tmp_path, monkeypatch) -> None:
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
                finish_reason="stop",
                payload={"result": AgentLoopResult(session_id=session_id or "session-1", model=request.model, content="Hello")},
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, events = _post_sse(
            f"{base_url}/agent/run/stream",
            {
                "session_id": "session-1",
                "model": "openai-compatible/demo-model",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert [event["event"] for event in events] == ["start", "assistant.tool_call.delta", "assistant.delta", "done"]
    assert [event["sequence"] for event in events] == [1, 2, 3, 4]
    assert all(event["trace_id"] == "trace-1" for event in events)
    assert all(event["event_id"] for event in events)
    assert events[1]["tool_calls"][0]["name"] == "echo_text"
    assert events[-1]["is_terminal"] is True
    assert events[-1]["payload"]["result"]["content"] == "Hello"


def test_sidecar_http_server_streams_terminal_error_event_on_agent_loop_failure(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            raise RuntimeError("stream exploded")

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, events = _post_sse(
            f"{base_url}/agent/run/stream",
            {
                "session_id": "session-error",
                "model": "openai-compatible/demo-model",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert len(events) == 1
    assert events[0]["event"] == "error"
    assert events[0]["is_terminal"] is True
    assert events[0]["sequence"] == 1
    assert bool(events[0]["event_id"])
    assert bool(events[0]["trace_id"])
    assert events[0]["session_id"] == "session-error"
    assert events[0]["error"]["code"] == "AGENT_LOOP_STREAM_FAILED"
