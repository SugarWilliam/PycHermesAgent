import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pyc_hermes_agent import SidecarClient
from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import AgentLoopRequest, MetaAnalysisRequest, RetrievalRequest
from pyc_hermes_agent.mrag_core.ownership import MRAG_LOCK_FILE
from pyc_hermes_agent.sidecar_api import create_http_server
from pyc_hermes_agent.sidecar_api.service import SIDECAR_API_VERSION

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


def _get_json_with_headers(url: str) -> tuple[int, dict, dict[str, str]]:
    with urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers.items())


def _get_json_with_request_id(url: str, request_id: str) -> tuple[int, dict, dict[str, str]]:
    request = Request(url, headers={"X-Pyc-Request-Id": request_id}, method="GET")
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers.items())


def _post_json_with_headers(url: str, payload: dict) -> tuple[int, dict, dict[str, str]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers.items())


def _post_json_error_with_headers(url: str, payload: dict) -> tuple[int, dict, dict[str, str]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8")), dict(response.headers.items())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8")), dict(exc.headers.items())


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


def _post_sse_with_headers(url: str, payload: dict) -> tuple[int, list[dict], dict[str, str]]:
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
        return response.status, [json.loads(chunk) for chunk in chunks], dict(response.headers.items())


def _post_sse_with_request_id(url: str, payload: dict, request_id: str) -> tuple[int, list[dict], dict[str, str]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream", "X-Pyc-Request-Id": request_id},
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
        return response.status, [json.loads(chunk) for chunk in chunks], dict(response.headers.items())


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


def test_sidecar_http_server_sets_api_version_header_on_json_success(tmp_path) -> None:
    _make_fake_hermes_checkout(tmp_path)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload, headers = _get_json_with_headers(f"{base_url}/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert payload["sidecar_api_version"] == SIDECAR_API_VERSION
    assert headers["X-Pyc-Sidecar-Api-Version"] == SIDECAR_API_VERSION
    assert headers["X-Pyc-Request-Id"]


def test_sidecar_http_server_sets_api_version_header_on_json_error(tmp_path) -> None:
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload, headers = _post_json_error_with_headers(
            f"{base_url}/knowledge-bases",
            {"name": ""},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 400
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "INVALID_REQUEST"
    assert payload["error"]["category"] == "request"
    assert payload["error"]["retryable"] is False
    assert payload["error"]["degraded"] is False
    assert payload["error"]["details"]["path"] == "/knowledge-bases"
    assert payload["error"]["details"]["method"] == "POST"
    assert payload["error"]["details"]["http_status"] == 400
    assert payload["error"]["details"]["request_id"] == headers["X-Pyc-Request-Id"]
    assert headers["X-Pyc-Sidecar-Api-Version"] == SIDECAR_API_VERSION
    assert headers["X-Pyc-Request-Id"]


def test_sidecar_http_server_returns_standard_error_response_for_unknown_route(tmp_path) -> None:
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload, headers = _post_json_error_with_headers(
            f"{base_url}/unknown-route",
            {},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 404
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["category"] == "transport"
    assert payload["error"]["details"]["path"] == "/unknown-route"
    assert payload["error"]["details"]["method"] == "POST"
    assert payload["error"]["details"]["http_status"] == 404
    assert payload["error"]["details"]["request_id"] == headers["X-Pyc-Request-Id"]


def test_sidecar_http_server_returns_storage_error_when_mrag_locked(tmp_path) -> None:
    mrag_root = ensure_runtime_directories(resolve_runtime_paths(tmp_path)).mrag_dir
    (mrag_root / MRAG_LOCK_FILE).write_text(
        json.dumps({"owner_id": "external-owner", "pid": 999999}, ensure_ascii=True),
        encoding="utf-8",
    )
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload, headers = _post_json_error_with_headers(
            f"{base_url}/knowledge-bases",
            {"name": "locked"},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 423
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "MRAG_STORAGE_LOCKED"
    assert payload["error"]["category"] == "storage"
    assert payload["error"]["retryable"] is True
    assert payload["error"]["details"]["path"] == "/knowledge-bases"
    assert payload["error"]["details"]["http_status"] == 423
    assert payload["error"]["details"]["request_id"] == headers["X-Pyc-Request-Id"]


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


def test_sidecar_http_server_returns_error_status_for_failed_formal_analysis(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FailingFramework:
        def execute(self, request):
            raise RuntimeError("analysis exploded")

    monkeypatch.setattr(sidecar_service, "MetaFramework", lambda: _FailingFramework())
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, payload, headers = _post_json_error_with_headers(
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

    assert status_code == 502
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "FORMAL_ANALYSIS_FAILED"
    assert payload["error"]["category"] == "internal"
    assert payload["events"][-1]["type"] == "task.failed"
    assert headers["X-Pyc-Sidecar-Api-Version"] == SIDECAR_API_VERSION
    assert headers["X-Pyc-Request-Id"]


def test_sidecar_http_server_logs_health_status_transition_once_per_change(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import http_server as sidecar_http_server

    log_calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(sidecar_http_server, "log_event", lambda event, **fields: log_calls.append((event, fields)))
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        _get_json(f"{base_url}/health")
        _get_json(f"{base_url}/health")
        _make_fake_hermes_checkout(tmp_path)
        _get_json(f"{base_url}/health")
        _get_json(f"{base_url}/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    transitions = [fields for event, fields in log_calls if event == "sidecar.health.transition"]

    assert len(transitions) == 2
    assert transitions[0]["previous_status_label"] is None
    assert transitions[0]["status_label"] == "unavailable"
    assert transitions[0]["degraded"] is True
    assert transitions[0]["request_id"]
    assert transitions[1]["previous_status_label"] == "unavailable"
    assert transitions[1]["status_label"] == "ready-with-warnings"
    assert transitions[1]["degraded"] is False
    assert transitions[1]["request_id"]


def test_sidecar_http_server_correlates_request_logs_and_response_header(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import http_server as sidecar_http_server

    log_calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(sidecar_http_server, "log_event", lambda event, **fields: log_calls.append((event, fields)))
    _make_fake_hermes_checkout(tmp_path)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, _payload, headers = _get_json_with_headers(f"{base_url}/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    started = next(fields for event, fields in log_calls if event == "http.request.started")
    finished = next(fields for event, fields in log_calls if event == "http.request.finished")
    request_id = headers["X-Pyc-Request-Id"]

    assert status_code == 200
    assert request_id
    assert started["request_id"] == request_id
    assert finished["request_id"] == request_id
    assert started["path"] == "/health"
    assert finished["path"] == "/health"
    assert finished["status"] == 200


def test_sidecar_http_server_honors_incoming_request_id(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import http_server as sidecar_http_server

    log_calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(sidecar_http_server, "log_event", lambda event, **fields: log_calls.append((event, fields)))
    _make_fake_hermes_checkout(tmp_path)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    request_id = "req-from-client-123"

    try:
        status_code, _payload, headers = _get_json_with_request_id(f"{base_url}/health", request_id)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    started = next(fields for event, fields in log_calls if event == "http.request.started")
    finished = next(fields for event, fields in log_calls if event == "http.request.finished")

    assert status_code == 200
    assert headers["X-Pyc-Request-Id"] == request_id
    assert started["request_id"] == request_id
    assert finished["request_id"] == request_id


def test_sidecar_http_server_sets_request_id_header_on_sse(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopEvent

            yield AgentLoopEvent(
                event_id="event-1",
                trace_id="trace-1",
                sequence=1,
                event="done",
                is_terminal=True,
                session_id=session_id or "session-1",
                model=request.model,
                content="Hello",
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, events, headers = _post_sse_with_headers(
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
    assert headers["X-Pyc-Request-Id"]
    assert events[-1]["event"] == "done"


def test_sidecar_http_server_adds_request_id_to_sse_events(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopEvent

            yield AgentLoopEvent(
                event_id="event-1",
                trace_id="trace-1",
                sequence=1,
                event="start",
                session_id=session_id or "session-1",
                model=request.model,
            )
            yield AgentLoopEvent(
                event_id="event-2",
                trace_id="trace-1",
                sequence=2,
                event="done",
                is_terminal=True,
                session_id=session_id or "session-1",
                model=request.model,
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    request_id = "req-sse-client-456"

    try:
        status_code, events, headers = _post_sse_with_request_id(
            f"{base_url}/agent/run/stream",
            {"model": "openai-compatible/demo-model", "messages": [{"role": "user", "content": "stream"}]},
            request_id,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status_code == 200
    assert headers["X-Pyc-Request-Id"] == request_id
    assert [event["request_id"] for event in events] == [request_id, request_id]
    assert all(event["trace_id"] == "trace-1" for event in events)


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


def test_sidecar_http_server_sets_api_version_header_on_sse(tmp_path, monkeypatch) -> None:
    from pyc_hermes_agent.sidecar_api import service as sidecar_service

    class _FakeAgentLoop:
        def __init__(self, *, root=None):
            self.root = root

        def stream(self, request, *, max_iterations=8, session_id=None, planning_enabled=True, retry_budget=1):
            from pyc_hermes_agent.contracts import AgentLoopEvent

            yield AgentLoopEvent(
                event_id="event-1",
                trace_id="trace-1",
                sequence=1,
                event="done",
                is_terminal=True,
                session_id=session_id or "session-1",
                model=request.model,
                content="Hello",
            )

    monkeypatch.setattr(sidecar_service, "AgentLoop", _FakeAgentLoop)
    server, thread = _start_server(root=tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        status_code, events, headers = _post_sse_with_headers(
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
    assert headers["X-Pyc-Sidecar-Api-Version"] == SIDECAR_API_VERSION
    assert headers["X-Pyc-Request-Id"]
    assert events[-1]["event"] == "done"


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
