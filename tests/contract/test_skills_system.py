"""Contract tests for the Skills system (E1 + E2)."""

from __future__ import annotations

from pyc_hermes_agent.hermes_engine.skills import SkillRegistry, register_builtin_skills


def _fresh_registry() -> SkillRegistry:
    registry = SkillRegistry()
    register_builtin_skills(registry)
    return registry


def test_skill_registry_list_builtins() -> None:
    registry = _fresh_registry()
    skills = registry.list_all()
    assert len(skills) >= 8


def test_skill_activate_deactivate() -> None:
    registry = _fresh_registry()
    assert registry.activate("structured-report") is True
    active = registry.list_active()
    assert any(s.id == "structured-report" for s in active)

    assert registry.deactivate("structured-report") is True
    active = registry.list_active()
    assert not any(s.id == "structured-report" for s in active)


def test_active_prompt_fragments() -> None:
    registry = _fresh_registry()
    registry.activate("structured-report")
    registry.activate("swot-analysis")
    fragments = registry.get_active_prompt_fragments()
    assert len(fragments) == 2
    assert all(isinstance(f, str) and len(f) > 20 for f in fragments)


def test_skill_categories() -> None:
    registry = _fresh_registry()
    categories = {s.category for s in registry.list_all()}
    assert "prompt" in categories
    assert "analysis" in categories


def test_double_activate_idempotent() -> None:
    registry = _fresh_registry()
    registry.activate("executive-summary")
    registry.activate("executive-summary")
    active = registry.list_active()
    ids = [s.id for s in active]
    assert ids.count("executive-summary") == 1
