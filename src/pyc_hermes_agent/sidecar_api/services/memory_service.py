"""Sidecar service functions for memory/preferences management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.hermes_engine.memory import UserPreferences, preferences_path

_PREFERENCE_KEYS = frozenset(
    {"language", "analysis_conservatism", "preferred_output_style", "domain_hints", "custom_instructions"}
)


def _preferences_audit_log_path(workspace_root: Path) -> Path:
    paths = ensure_runtime_directories(resolve_runtime_paths(workspace_root))
    audit_dir = paths.local_data_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir / "preferences.jsonl"


def _append_preferences_audit(
    *,
    workspace_root: Path,
    keys_touched: list[str],
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> None:
    line = json.dumps(
        {
            "event": "preferences_update",
            "keys": keys_touched,
            "before": before,
            "after": after,
        },
        ensure_ascii=True,
    )
    audit_path = _preferences_audit_log_path(workspace_root.resolve())
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def get_preferences(root: Path | None) -> Dict[str, Any]:
    """Load and return current preferences."""
    path = preferences_path(Path(root) if root else Path("."))
    prefs = UserPreferences.load(path)
    return _prefs_to_dict(prefs)


def update_preferences(root: Path | None, partial: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial updates into preferences and save."""
    workspace = Path(root) if root else Path(".")
    path = preferences_path(workspace)
    prefs = UserPreferences.load(path)
    before = _prefs_to_dict(prefs)
    keys_touched = sorted(k for k in partial if k in _PREFERENCE_KEYS)
    prefs.merge(partial)
    prefs.save(path)
    after = _prefs_to_dict(prefs)
    try:
        if keys_touched:
            _append_preferences_audit(workspace_root=workspace, keys_touched=keys_touched, before=before, after=after)
    except OSError:
        # Audit is best-effort; preference save already succeeded.
        pass
    return after


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
