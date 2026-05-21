from pyc_hermes_agent.contracts import ChatMessage, ToolCall
from pyc_hermes_agent.hermes_engine import AgentSessionStore, SessionMessageMatch, SessionRecallMatch, SessionRecallStore


def test_session_recall_store_searches_messages_and_sessions(tmp_path) -> None:
    store = AgentSessionStore(root=tmp_path)
    store.save(
        session_id="session-alpha",
        model="openai-compatible/demo-model",
        messages=[
            ChatMessage(role="user", content="Need help with docker networking on Windows"),
            ChatMessage(role="assistant", content="Use a bridge network and verify the firewall rules."),
        ],
    )
    store.save(
        session_id="session-beta",
        model="openai-compatible/demo-model",
        messages=[ChatMessage(role="user", content="Discuss release notes")],
    )
    recall = SessionRecallStore(root=tmp_path, session_store=store)

    message_matches = recall.search_messages("docker")
    session_matches = recall.search_sessions("docker")

    assert isinstance(message_matches[0], SessionMessageMatch)
    assert message_matches[0].session_id == "session-alpha"
    assert message_matches[0].role == "user"
    assert "docker networking on Windows" in message_matches[0].excerpt
    assert isinstance(session_matches[0], SessionRecallMatch)
    assert session_matches[0].session_id == "session-alpha"
    assert session_matches[0].match_count >= 1
    assert session_matches[0].message_count == 2


def test_session_recall_store_searches_tool_call_metadata(tmp_path) -> None:
    store = AgentSessionStore(root=tmp_path)
    store.save(
        session_id="session-tools",
        model="openai-compatible/demo-model",
        messages=[
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[ToolCall(name="web_search", arguments='{"query": "Copilot auth headers"}')],
            )
        ],
    )
    recall = SessionRecallStore(root=tmp_path, session_store=store)

    message_matches = recall.search_messages("web_search")

    assert message_matches[0].session_id == "session-tools"
    assert "web_search" in message_matches[0].excerpt


def test_session_recall_store_returns_no_results_for_blank_query(tmp_path) -> None:
    recall = SessionRecallStore(root=tmp_path)

    assert recall.search_messages("   ") == []
    assert recall.search_sessions("") == []
