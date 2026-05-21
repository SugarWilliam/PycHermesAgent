"""Install-directory immutability checks (engineering preview, not a full installer)."""

from __future__ import annotations

from pathlib import Path

from pyc_hermes_agent.common.runtime_paths import RuntimePaths

_WRITABLE_ATTRS = (
    "config_dir",
    "local_data_dir",
    "logs_dir",
    "cache_dir",
    "downloads_dir",
    "indexes_dir",
    "models_dir",
    "artifacts_dir",
    "mrag_dir",
)


def validate_runtime_paths_outside_install(paths: RuntimePaths, install_dir: Path) -> None:
    """Ensure no writable runtime directory is contained under *install_dir*."""
    inst = install_dir.resolve()
    for name in _WRITABLE_ATTRS:
        candidate = getattr(paths, name).resolve()
        if candidate == inst:
            raise RuntimeError(
                f"Packaging violation: {name} equals install_dir {inst}. "
                "Configuration and data must live under APPDATA / LOCALAPPDATA (or XDG on POSIX)."
            )
        try:
            candidate.relative_to(inst)
        except ValueError:
            continue
        raise RuntimeError(
            f"Packaging violation: {name}={candidate} is inside read-only install_dir {inst}."
        )
