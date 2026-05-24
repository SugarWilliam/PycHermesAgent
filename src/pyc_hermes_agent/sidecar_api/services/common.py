"""Shared utilities for sidecar service modules."""

from __future__ import annotations

import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

from pyc_hermes_agent import __version__
from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import ErrorEnvelope, EventEnvelope
from pyc_hermes_agent.sidecar_api.error_domains import DOMAIN_INTERNAL
from pyc_hermes_agent.sidecar_api.logging import log_event  # noqa: F401 - re-exported


SIDECAR_API_VERSION = "0.9"
MRAG_RETRIEVAL_MODES = ["lexical", "semantic", "hybrid"]
MRAG_RUNTIME_NOTE = "JSON-backed MRAGService is the active sidecar runtime; SQLite/FTS5 artifacts exist separately and are not the active sidecar backend."


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_runtime_directories_root(root: Path | None = None) -> Path | None:
    if root is None:
        return None
    return root.resolve()


def _serialize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _event(source: str, event_type: str, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _serialize(EventEnvelope(source=source, type=event_type, task_id=task_id, payload=payload))


def _error(
    code: str,
    category: str,
    message: str,
    *,
    domain: str = DOMAIN_INTERNAL,
    retryable: bool = False,
    degraded: bool = False,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return _serialize(
        ErrorEnvelope(
            code=code,
            category=category,
            domain=domain,
            message=message,
            retryable=retryable,
            degraded=degraded,
            details=details or {},
        )
    )


def make_error_response(
    code: str,
    category: str,
    message: str,
    *,
    domain: str = DOMAIN_INTERNAL,
    retryable: bool = False,
    degraded: bool = False,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "status": "error",
        "error": _error(
            code,
            category,
            message,
            domain=domain,
            retryable=retryable,
            degraded=degraded,
            details=details,
        ),
    }


def get_mrag_runtime_snapshot(*, include_note: bool = False) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "backend": "json",
        "retrieval_modes": list(MRAG_RETRIEVAL_MODES),
    }
    if include_note:
        snapshot["note"] = MRAG_RUNTIME_NOTE
    return snapshot


def get_health(root: Path | None = None) -> dict:
    from pyc_hermes_agent.sidecar_api.services.skill_service import get_hermes_bridge_health

    bridge_health = get_hermes_bridge_health(root)
    ready_state = "unavailable"
    if bridge_health["bridge_ready"]:
        ready_state = "ready"
    elif bridge_health["checkout_present"] and bridge_health["import_ready"]:
        ready_state = "degraded"
    status_label = ready_state
    if ready_state == "ready" and bridge_health["warnings"]:
        status_label = "ready-with-warnings"

    observability: Dict[str, Any] = {
        "structured_log_events": True,
        "log_format_env": "PYC_HERMES_LOG_FORMAT",
        "log_level_env": "PYC_HERMES_LOG_LEVEL",
        "disable_file_log_env": "PYC_HERMES_DISABLE_FILE_LOG",
    }
    if root is not None:
        resolved_root = Path(root).resolve()
        paths = ensure_runtime_directories(resolve_runtime_paths(resolved_root))
        observability["logs_dir"] = str(paths.logs_dir)
        observability["sidecar_events_log"] = str(paths.logs_dir / "sidecar-events.log")

    return {
        "healthy": ready_state != "unavailable",
        "degraded": ready_state != "ready",
        "status_label": status_label,
        "version": __version__,
        "sidecar_api_version": SIDECAR_API_VERSION,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "mrag_retrieval_modes": list(MRAG_RETRIEVAL_MODES),
        "mrag_runtime": get_mrag_runtime_snapshot(),
        "observability": observability,
        "hermes": {
            "ready_state": ready_state,
            "status_label": status_label,
            "checkout_present": bridge_health["checkout_present"],
            "worktree_state": bridge_health["worktree_state"],
            "import_ready": bridge_health["import_ready"],
            "bridge_ready": bridge_health["bridge_ready"],
            "bridged_surfaces": bridge_health["bridged_surfaces"],
            "blocked_surfaces": bridge_health["blocked_surfaces"],
            "bridged_count": bridge_health["bridged_count"],
            "surface_count": bridge_health["surface_count"],
        },
    }


def get_runtime_paths_snapshot(root: Path | None = None) -> Dict[str, str]:
    """Resolved writable runtime directories (strings for JSON and desktop shells)."""
    base = resolve_runtime_directories_root(root)
    paths = ensure_runtime_directories(resolve_runtime_paths(base))
    return {
        "config_dir": str(paths.config_dir),
        "local_data_dir": str(paths.local_data_dir),
        "logs_dir": str(paths.logs_dir),
        "cache_dir": str(paths.cache_dir),
        "downloads_dir": str(paths.downloads_dir),
        "indexes_dir": str(paths.indexes_dir),
        "models_dir": str(paths.models_dir),
        "artifacts_dir": str(paths.artifacts_dir),
        "mrag_dir": str(paths.mrag_dir),
    }


def get_config_snapshot(root: Path | None = None) -> Dict[str, Any]:
    from pyc_hermes_agent.llm_gateway import resolve_opencode_like_config

    base = root or _repo_root()
    resolved = resolve_opencode_like_config(base)
    return {
        "config_path": str(resolved.config_path) if resolved.config_path else None,
        "default_model": resolved.default_model,
        "small_model": resolved.small_model,
        "free_first": resolved.free_first,
        "mrag_runtime": get_mrag_runtime_snapshot(include_note=True),
    }


def list_providers(root: Path | None = None):
    from pyc_hermes_agent.llm_gateway import resolve_opencode_like_config

    base = root or _repo_root()
    resolved = resolve_opencode_like_config(base)
    providers = []
    for provider in resolved.providers.values():
        providers.append(
            {
                "id": provider.id,
                "name": provider.name,
                "first_class": provider.first_class,
                "free_first": provider.free_first,
                "default_model_id": provider.default_model_id,
                "default_small_model_id": provider.default_small_model_id,
                "auth_methods": [
                    {
                        "id": method.id,
                        "label": method.label,
                        "kind": method.kind,
                        "enterprise_supported": method.enterprise_supported,
                    }
                    for method in provider.auth_methods
                ],
            }
        )
    return sorted(providers, key=lambda item: (not item["first_class"], item["name"].lower()))


def list_models(root: Path | None = None):
    from pyc_hermes_agent.llm_gateway import resolve_opencode_like_config

    base = root or _repo_root()
    resolved = resolve_opencode_like_config(base)
    return [
        {
            "id": model.id,
            "provider_id": model.provider_id,
            "model_id": model.model_id,
            "name": model.name,
            "free": model.free,
            "tags": model.tags,
            "supports_tools": model.supports_tools,
            "supports_vision": model.supports_vision,
            "supports_reasoning": model.supports_reasoning,
            "featured_rank": model.featured_rank,
            "source": model.source,
            "variants": sorted(model.variants.keys()),
        }
        for model in resolved.models
    ]


def list_rules(root: Path | None = None):
    from pyc_hermes_agent.llm_gateway.rules import discover_ordered_rule_documents

    base = root or _repo_root()
    docs = discover_ordered_rule_documents(base)
    return [{"path": str(path), "name": path.name, "precedence_order": index} for index, path in enumerate(docs)]


def list_asset_inventory(root: Path | None = None) -> Dict[str, Any]:
    from pyc_hermes_agent.asset_manager import AssetManager

    base = root or _repo_root()
    manager = AssetManager(root=base)
    return {"items": manager.list_installed_assets()}


def list_sidecar_artifacts(root: Path | None = None, *, task_id: str | None = None) -> Dict[str, Any]:
    from pyc_hermes_agent.artifact_engine import ArtifactEngine

    base = root or _repo_root()
    engine = ArtifactEngine(root=base)
    if task_id is None:
        records = engine.list_all_artifacts()
    else:
        records = engine.list_task_artifacts(task_id)
    return {
        "items": [_artifact_record_payload(record) for record in records],
        "task_id": task_id,
    }


def _artifact_record_payload(record) -> Dict[str, Any]:
    return {
        "artifact_id": record.artifact_id,
        "task_id": record.task_id,
        "name": record.name,
        "media_type": record.media_type,
        "path": str(record.path),
        "metadata_path": str(record.metadata_path),
        "size_bytes": record.size_bytes,
        "checksum": record.checksum,
        "created_at_ns": record.created_at_ns,
        "artifact_format_version": record.artifact_format_version,
    }
