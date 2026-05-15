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


def resolve_runtime_paths(root: Path | None = None, *, app_name: str = "PycHermesAgent") -> RuntimePaths:
    if root is not None:
        sandbox_root = Path(root).resolve() / ".pyc_hermes_agent_runtime"
        config_dir = sandbox_root / "APPDATA" / app_name
        local_data_dir = sandbox_root / "LOCALAPPDATA" / app_name
    else:
        home = Path.home()
        config_dir = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")) / app_name
        local_data_dir = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / app_name

    return RuntimePaths(
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
