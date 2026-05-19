"""Integration tests: real HTTP server → service → response flows."""

import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from pyc_hermes_agent.sidecar_api import create_http_server


def _start_server(*, root=None):
    server = create_http_server(port=0, root=root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _base_url(server):
    return f"http://127.0.0.1:{server.server_address[1]}"


def _get(url: str, timeout: int = 10):
    with urlopen(url, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get_raw(url: str, timeout: int = 10):
    """Return status + headers; body may be empty."""
    with urlopen(url, timeout=timeout) as resp:
        return resp.status, resp.read(), dict(resp.headers.items())


def _post(url: str, payload: dict, timeout: int = 10):
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _put(url: str, payload: dict, timeout: int = 10):
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _delete(url: str, timeout: int = 10):
    req = Request(url, method="DELETE")
    with urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _http_error(method: str, url: str, payload: dict | None = None, timeout: int = 10):
    """Make request expecting an HTTP error; return (status, body_dict)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


@pytest.fixture()
def server_url(tmp_path):
    """Start server, yield base URL, tear down after test."""
    server, thread = _start_server(root=tmp_path)
    yield _base_url(server)
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_health_endpoint_returns_200(server_url: str) -> None:
    status, body = _get(f"{server_url}/health")
    assert status == 200
    assert "status_label" in body
    assert "sidecar_api_version" in body


def test_agent_run_returns_response(server_url: str) -> None:
    """POST /agent/run — may error due to no LLM but returns structured response."""
    status, body = _http_error(
        "POST",
        f"{server_url}/agent/run",
        {
            "model": "openai-compatible/nonexistent",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    # Either 200 with result or structured error
    assert isinstance(body, dict)
    if status != 200:
        assert "error" in body or "status" in body


def test_preferences_crud_cycle(server_url: str) -> None:
    # GET default
    s1, initial = _get(f"{server_url}/preferences")
    assert s1 == 200
    assert "language" in initial

    # PUT update
    s2, updated = _put(f"{server_url}/preferences", {"language": "zh"})
    assert s2 == 200
    assert updated["language"] == "zh"

    # GET verify
    s3, loaded = _get(f"{server_url}/preferences")
    assert s3 == 200
    assert loaded["language"] == "zh"

    # DELETE reset
    s4, reset = _delete(f"{server_url}/preferences")
    assert s4 == 200

    # GET verify reset
    s5, final = _get(f"{server_url}/preferences")
    assert s5 == 200
    assert final["language"] == initial["language"]


def test_knowledge_base_create_and_list(server_url: str) -> None:
    s1, kb = _post(f"{server_url}/knowledge-bases", {"name": "integ-kb"})
    assert s1 == 201
    assert "knowledge_base_id" in kb

    s2, listing = _get(f"{server_url}/knowledge-bases")
    assert s2 == 200
    # listing may be a list or a dict with items
    items = listing if isinstance(listing, list) else listing.get("items", listing)
    ids = [item["knowledge_base_id"] for item in items]
    assert kb["knowledge_base_id"] in ids


def test_formal_analysis_returns_structured_result(server_url: str) -> None:
    status, body = _post(
        f"{server_url}/formal-analysis",
        {
            "problem_statement": "network pagerank analysis",
            "data": {"adjacency": [[0.0, 1.0], [1.0, 0.0]]},
            "params": {"analysis": "pagerank"},
        },
    )
    assert status == 200
    assert "analysis" in body
    analysis = body["analysis"]
    assert "selected_method" in analysis


def test_cors_headers_not_present_by_default(server_url: str) -> None:
    status, _body, headers = _get_raw(f"{server_url}/health")
    assert status == 200
    assert "Access-Control-Allow-Origin" not in headers


def test_404_for_unknown_route(server_url: str) -> None:
    status, body = _http_error("GET", f"{server_url}/nonexistent")
    assert status == 404
    assert body["status"] == "error"
    assert body["error"]["code"] == "NOT_FOUND"
