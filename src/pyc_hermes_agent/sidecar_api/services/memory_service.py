"""Sidecar service functions for memory/preferences management."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pyc_hermes_agent.hermes_engine.memory import UserPreferences, preferences_path


def get_preferences(root: Path | None) -> Dict[str, Any]:
    """Load and return current preferences."""
    path = preferences_path(Path(root) if root else Path("."))
    prefs = UserPreferences.load(path)
    return _prefs_to_dict(prefs)


def update_preferences(root: Path | None, partial: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial updates into preferences and save."""
    path = preferences_path(Path(root) if root else Path("."))
    prefs = UserPreferences.load(path)
    prefs.merge(partial)
    prefs.save(path)
    return _prefs_to_dict(prefs)


def reset_preferences(root: Path | None) -> Dict[str, Any]:
    """Reset preferences to defaults and save."""
    path = preferences_path(Path(root) if root else Path("."))
    prefs = UserPreferences()
    prefs.save(path)
    return _prefs_to_dict(prefs)


def _prefs_to_dict(prefs: UserPreferences) -> Dict[str, Any]:
    return {
        "language": prefs.language,
        "analysis_conservatism": prefs.analysis_conservatism,
        "preferred_output_style": prefs.preferred_output_style,
        "domain_hints": prefs.domain_hints,
        "custom_instructions": prefs.custom_instructions,
    }


__all__ = ["get_preferences", "reset_preferences", "update_preferences"]
