"""Runtime path helpers aligned to local-first packaging rules."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    config_dir: Path
    local_data_dir: Path
    logs_dir: Path
    cache_dir: Path
    downloads_dir: Path
    indexes_dir: Path
    models_dir: Path
    artifacts_dir: Path
    mrag_dir: Path


def _packaging_rules_enforced() -> bool:
    return os.environ.get("PYC_HERMES_ENFORCE_PACKAGING_RULES", "").strip().lower() in {"1", "true", "yes"}


def _maybe_validate_against_install_dir(paths: RuntimePaths) -> None:
    raw = os.environ.get("PYC_HERMES_INSTALL_DIR", "").strip()
    if not raw or not _packaging_rules_enforced():
        return
    from pyc_hermes_agent.packaging.policy import validate_runtime_paths_outside_install

    validate_runtime_paths_outside_install(paths, Path(raw))


def resolve_runtime_paths(root: Path | None = None, *, app_name: str = "PycHermesAgent") -> RuntimePaths:
    """Resolve writable runtime directories.

    * When *root* is set and packaging rules are **not** enforced (default dev/test),
      all writable paths stay under ``root/.pyc_hermes_agent_runtime/...`` (sandbox).
    * When ``PYC_HERMES_ENFORCE_PACKAGING_RULES`` is truthy, *root* is ignored for
      writable layout: paths follow Windows ``%APPDATA%`` / ``%LOCALAPPDATA%`` or
      POSIX XDG config/data dirs — required for read-only install directories.
    * When *root* is None and packaging is not enforced, POSIX hosts use XDG; Windows
      uses normal user profile locations.
    """
    use_workspace_sandbox = root is not None and not _packaging_rules_enforced()
    if use_workspace_sandbox:
        sandbox_root = Path(root).resolve() / ".pyc_hermes_agent_runtime"
        config_dir = sandbox_root / "APPDATA" / app_name
        local_data_dir = sandbox_root / "LOCALAPPDATA" / app_name
    elif os.name == "nt":
        home = Path.home()
        config_dir = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")) / app_name
        local_data_dir = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / app_name
    elif "APPDATA" in os.environ and "LOCALAPPDATA" in os.environ:
        # Allow CI / POSIX hosts to simulate Windows layout (packaging contract tests).
        config_dir = Path(os.environ["APPDATA"]) / app_name
        local_data_dir = Path(os.environ["LOCALAPPDATA"]) / app_name
    else:
        home = Path.home()
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / app_name
        local_data_dir = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / app_name

    paths = RuntimePaths(
        config_dir=config_dir,
        local_data_dir=local_data_dir,
        logs_dir=local_data_dir / "logs",
        cache_dir=local_data_dir / "cache",
        downloads_dir=local_data_dir / "downloads",
        indexes_dir=local_data_dir / "indexes",
        models_dir=local_data_dir / "models",
        artifacts_dir=local_data_dir / "artifacts",
        mrag_dir=local_data_dir / "mrag_core",
    )
    _maybe_validate_against_install_dir(paths)
    return paths


def ensure_runtime_directories(paths: RuntimePaths) -> RuntimePaths:
    for path in (
        paths.config_dir,
        paths.local_data_dir,
        paths.logs_dir,
        paths.cache_dir,
        paths.downloads_dir,
        paths.indexes_dir,
        paths.models_dir,
        paths.artifacts_dir,
        paths.mrag_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


__all__ = ["RuntimePaths", "ensure_runtime_directories", "resolve_runtime_paths"]
