"""Contract receipts for Evolution backlog strands (working memory, audit, MRAG drafts, patch drafts)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import AgentLoopRequest, ChatCompletionRequest, ChatMessage
from pyc_hermes_agent.hermes_engine import AgentLoop, AgentSessionStore
from pyc_hermes_agent.llm_gateway import LLMChatResponse
from pyc_hermes_agent.sidecar_api.services._normalize import normalize_agent_loop_request
from pyc_hermes_agent.sidecar_api.services.memory_service import update_preferences

from .test_sidecar_http import _get_json, _post_json, _start_server


def _delete_json(url: str) -> tuple[int, dict]:
    request = Request(url, method="DELETE")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_normalize_agent_loop_request_coerces_working_memory_list() -> None:
    normalized = normalize_agent_loop_request(
        AgentLoopRequest(
            messages=[ChatMessage(role="user", content="hello")],
            working_memory=["a", 1, None],
            update_working_memory=True,
        )
    )
    assert normalized.working_memory == ["a", "1", "None"]
    assert normalized.update_working_memory is True


def test_session_store_round_trips_working_memory(tmp_path: Path) -> None:
    store = AgentSessionStore(root=tmp_path)
    store.save(
        session_id="wm-roundtrip",
        model="demo-model",
        messages=[ChatMessage(role="user", content="hi")],
        working_memory=[" line one ", "two"],
    )
    loaded = store.load("wm-roundtrip")
    assert loaded is not None
    assert loaded.working_memory == ["line one", "two"]


def test_normalize_working_memory_lines_bounds_length() -> None:
    from pyc_hermes_agent.hermes_engine.session_store import (
        _MAX_WORKING_MEMORY_LINE_CHARS,
        normalize_working_memory_lines,
    )

    long = "z" * (_MAX_WORKING_MEMORY_LINE_CHARS + 50)
    out = normalize_working_memory_lines([long])
    assert len(out[0]) == _MAX_WORKING_MEMORY_LINE_CHARS


def test_preferences_put_appends_audit_jsonl(tmp_path: Path) -> None:
    prefs = tmp_path / "config" / "preferences.json"
    prefs.parent.mkdir(parents=True)
    prefs.write_text(
        json.dumps(
            {"language": "en", "analysis_conservatism": "moderate", "preferred_output_style": "structured"},
            indent=2,
        ),
        encoding="utf-8",
    )

    snapshot = update_preferences(tmp_path, {"language": "zh"})

    assert snapshot["language"] == "zh"
    audit_path = ensure_runtime_directories(resolve_runtime_paths(tmp_path)).local_data_dir / "audit" / "preferences.jsonl"
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    record = json.loads(lines[-1])
    assert record["event"] == "preferences_update"
    assert "language" in record["keys"]


def test_agent_loop_injects_working_memory_and_persists(tmp_path: Path) -> None:
    store = AgentSessionStore(root=tmp_path)
    store.save(
        session_id="sess-wm",
        model="openai-compatible/demo-model",
        messages=[
            ChatMessage(role="user", content="Older"),
            ChatMessage(role="assistant", content="Old reply"),
            *(ChatMessage(role="user", content=f"M{i}") for i in range(8)),
            *(ChatMessage(role="assistant", content=f"A{i}") for i in range(8)),
        ],
        working_memory=["remember: use metric"],
    )

    calls: list[object] = []

    def fake_llm_executor(request, _root):  # type: ignore[no-untyped-def]
        calls.append(request)
        assert any("<session-working-memory>" in msg.content for msg in request.messages if msg.role == "system")
        return LLMChatResponse(
            model="openai-compatible/demo-model",
            provider_id="openai-compatible",
            content="Sure.",
            finish_reason="stop",
        )

    loop = AgentLoop(root=tmp_path, storage_root=tmp_path, llm_executor=fake_llm_executor, session_store=store)
    result = loop.run(
        ChatCompletionRequest(model="openai-compatible/demo-model", messages=[ChatMessage(role="user", content="Ping")]),
        session_id="sess-wm",
    )

    assert result.working_memory == ["remember: use metric"]
    reloaded = store.load("sess-wm")
    assert reloaded is not None and reloaded.working_memory == ["remember: use metric"]

    loop.run(
        ChatCompletionRequest(model="openai-compatible/demo-model", messages=[ChatMessage(role="user", content="Ping2")]),
        session_id="sess-wm",
        update_working_memory=True,
        working_memory=["replacement note"],
        max_iterations=1,
    )

    assert store.load("sess-wm").working_memory == ["replacement note"]

    loop.run(
        ChatCompletionRequest(model="openai-compatible/demo-model", messages=[ChatMessage(role="user", content="Ping3")]),
        session_id="sess-wm",
        max_iterations=1,
    )

    assert store.load("sess-wm").working_memory == ["replacement note"]


    server, thread = _start_server(root=tmp_path)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        _, root_payload = _get_json(f"{base}/")
        routes = root_payload["routes"]
        assert "/knowledge-bases/{id}/materialize" in routes
        assert "/skills/patch-drafts" in routes

        kb_status, kb_body = _post_json(f"{base}/knowledge-bases", {"name": "Mat KB"})
        assert kb_status == 201
        kb_id = kb_body["knowledge_base_id"]

        mat_status, mat_body = _post_json(
            f"{base}/knowledge-bases/{kb_id}/materialize",
            {"text": "## Final draft\nFacts here.", "title": "Note A"},
        )
        assert mat_status == 201
        assert mat_body["title"] == "Note A"
        assert mat_body.get("metadata", {}).get("materialization") is True

        draft_status, draft = _post_json(
            f"{base}/skills/patch-drafts",
            {"title": "t1", "body": "```markdown\nprobe\n```"},
        )
        assert draft_status == 201
        draft_id = draft["draft_id"]

        list_status, listed = _get_json(f"{base}/skills/patch-drafts")
        assert list_status == 200
        assert listed["items"]

        server_store = AgentSessionStore(root=tmp_path)
        server_store.save(
            session_id="http-suggest",
            model="demo",
            messages=[
                ChatMessage(role="user", content="Ask"),
                ChatMessage(role="assistant", content="Heuristic excerpt for SKILL draft."),
            ],
        )

        sug_status, suggested = _post_json(
            f"{base}/skills/patch-drafts/suggest-from-session",
            {"session_id": "http-suggest"},
        )
        assert sug_status == 201
        assert suggested["source"] == "session_suggest"

        del_status, deleted = _delete_json(f"{base}/skills/patch-drafts/{draft_id}")
        assert del_status == 200
        assert deleted.get("draft_id") == draft_id

        missing_status, missing = _delete_json(f"{base}/skills/patch-drafts/{draft_id}")
        assert missing_status == 404
        assert missing.get("status") == "error"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
