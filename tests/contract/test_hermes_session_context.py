from pyc_hermes_agent.hermes_engine import bind_session_context, get_current_session_id


def test_bind_session_context_exposes_and_restores_current_session() -> None:
    assert get_current_session_id() is None

    with bind_session_context("session-1") as active_session_id:
        assert active_session_id == "session-1"
        assert get_current_session_id() == "session-1"

    assert get_current_session_id() is None


def test_bind_session_context_restores_outer_session_when_nested() -> None:
    with bind_session_context("outer"):
        assert get_current_session_id() == "outer"
        with bind_session_context("inner"):
            assert get_current_session_id() == "inner"
        assert get_current_session_id() == "outer"


def test_bind_session_context_normalizes_blank_values() -> None:
    with bind_session_context("   ") as active_session_id:
        assert active_session_id is None
        assert get_current_session_id() is None
