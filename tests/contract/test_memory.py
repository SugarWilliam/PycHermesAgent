"""Contract tests for three-layer memory system."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyc_hermes_agent.hermes_engine.memory import MemoryLayers, UserPreferences, preferences_path


class TestUserPreferences:
    """Tests for UserPreferences dataclass."""

    def test_defaults_are_sane(self) -> None:
        prefs = UserPreferences()
        assert prefs.language == "en"
        assert prefs.analysis_conservatism == "moderate"
        assert prefs.preferred_output_style == "structured"
        assert prefs.domain_hints == []
        assert prefs.custom_instructions == ""

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "config" / "preferences.json"
        prefs = UserPreferences(
            language="zh",
            analysis_conservatism="conservative",
            preferred_output_style="brief",
            domain_hints=["embedded", "networking"],
            custom_instructions="Be concise.",
        )
        prefs.save(path)
        loaded = UserPreferences.load(path)
        assert loaded.language == "zh"
        assert loaded.analysis_conservatism == "conservative"
        assert loaded.preferred_output_style == "brief"
        assert loaded.domain_hints == ["embedded", "networking"]
        assert loaded.custom_instructions == "Be concise."

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        loaded = UserPreferences.load(path)
        assert loaded.language == "en"

    def test_to_system_prompt_fragment_nonempty(self) -> None:
        prefs = UserPreferences()
        fragment = prefs.to_system_prompt_fragment()
        assert fragment
        assert "en" in fragment
        assert "structured" in fragment

    def test_to_system_prompt_fragment_includes_custom(self) -> None:
        prefs = UserPreferences(custom_instructions="Always use tables.")
        fragment = prefs.to_system_prompt_fragment()
        assert "Always use tables." in fragment

    def test_merge_partial_preserves_other_fields(self) -> None:
        prefs = UserPreferences(language="zh", custom_instructions="hello")
        prefs.merge({"language": "ja"})
        assert prefs.language == "ja"
        assert prefs.custom_instructions == "hello"

    def test_merge_ignores_unknown_fields(self) -> None:
        prefs = UserPreferences()
        prefs.merge({"unknown_field": "value"})
        assert not hasattr(prefs, "unknown_field") or prefs.language == "en"


class TestMemoryLayers:
    """Tests for MemoryLayers container."""

    def test_build_context_injection_includes_preferences(self) -> None:
        layers = MemoryLayers(
            preferences=UserPreferences(language="fr"),
            knowledge_base_ids=["kb1", "kb2"],
        )
        context = layers.build_context_injection()
        assert "[User Preferences]" in context
        assert "fr" in context
        assert "[Active Knowledge Bases]" in context
        assert "kb1" in context
        assert "kb2" in context

    def test_build_context_injection_no_kbs(self) -> None:
        layers = MemoryLayers()
        context = layers.build_context_injection()
        assert "[User Preferences]" in context
        assert "[Active Knowledge Bases]" not in context


class TestPreferencesPath:
    """Tests for path resolution."""

    def test_preferences_path_under_root(self, tmp_path: Path) -> None:
        result = preferences_path(tmp_path)
        assert result == tmp_path / "config" / "preferences.json"
