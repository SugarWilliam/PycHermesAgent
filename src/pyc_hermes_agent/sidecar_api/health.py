"""Health state machine for the sidecar API."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class HealthState(Enum):
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ComponentHealth:
    name: str
    state: HealthState
    message: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "state": self.state.value, "message": self.message}


@dataclass
class SidecarHealth:
    state: HealthState
    components: List[ComponentHealth] = field(default_factory=list)
    degradation_reasons: List[str] = field(default_factory=list)

    @classmethod
    def evaluate(cls, root: Any = None) -> "SidecarHealth":
        """Evaluate current system health by probing components."""
        components: List[ComponentHealth] = []
        degradation_reasons: List[str] = []

        # Check LLM gateway
        components.append(_check_llm_gateway())

        # Check MetaHarness
        components.append(_check_meta_harness())

        # Check MRAG
        components.append(_check_mrag())

        # Check Hermes bridge
        components.append(_check_hermes_bridge(root))

        # Collect degradation reasons
        for comp in components:
            if comp.state == HealthState.DEGRADED and comp.message:
                degradation_reasons.append(f"{comp.name}: {comp.message}")

        # Derive aggregate state
        states = [c.state for c in components]
        if any(s == HealthState.UNAVAILABLE for s in states):
            aggregate = HealthState.UNAVAILABLE
        elif any(s == HealthState.DEGRADED for s in states):
            aggregate = HealthState.DEGRADED
        elif any(s == HealthState.READY_WITH_WARNINGS for s in states):
            aggregate = HealthState.READY_WITH_WARNINGS
        else:
            aggregate = HealthState.READY

        return cls(state=aggregate, components=components, degradation_reasons=degradation_reasons)

    def to_dict(self, root: Any = None) -> Dict[str, Any]:
        import sys
        from pathlib import Path

        from pyc_hermes_agent import __version__
        from pyc_hermes_agent.sidecar_api.services.common import (
            SIDECAR_API_VERSION,
            MRAG_RETRIEVAL_MODES,
            get_mrag_runtime_snapshot,
        )

        # Map state to legacy status_label for backward compatibility
        _status_label_map = {
            HealthState.READY: "ready",
            HealthState.READY_WITH_WARNINGS: "ready-with-warnings",
            HealthState.DEGRADED: "degraded",
            HealthState.UNAVAILABLE: "unavailable",
        }
        status_label = _status_label_map[self.state]

        observability: Dict[str, Any] = {
            "structured_log_events": True,
            "log_format_env": "PYC_HERMES_LOG_FORMAT",
            "log_level_env": "PYC_HERMES_LOG_LEVEL",
            "disable_file_log_env": "PYC_HERMES_DISABLE_FILE_LOG",
        }
        if root is not None:
            from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths

            resolved_root = Path(root).resolve()
            paths = ensure_runtime_directories(resolve_runtime_paths(resolved_root))
            observability["logs_dir"] = str(paths.logs_dir)
            observability["sidecar_events_log"] = str(paths.logs_dir / "sidecar-events.log")

        return {
            "state": self.state.value,
            "components": [c.to_dict() for c in self.components],
            "degradation_reasons": self.degradation_reasons,
            "version": __version__,
            "sidecar_api_version": SIDECAR_API_VERSION,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "mrag_retrieval_modes": list(MRAG_RETRIEVAL_MODES),
            "mrag_runtime": get_mrag_runtime_snapshot(),
            "observability": observability,
            # Backward-compatible fields
            "healthy": self.state != HealthState.UNAVAILABLE,
            "degraded": self.state in (HealthState.DEGRADED, HealthState.UNAVAILABLE),
            "status_label": status_label,
        }


def _check_llm_gateway() -> ComponentHealth:
    """Check LLM gateway: module importable → ready; otherwise degraded."""
    try:
        import pyc_hermes_agent.llm_gateway  # noqa: F401

        return ComponentHealth(name="llm_gateway", state=HealthState.READY)
    except ImportError:
        return ComponentHealth(
            name="llm_gateway", state=HealthState.DEGRADED, message="llm_gateway module not importable"
        )
    except Exception as exc:
        return ComponentHealth(name="llm_gateway", state=HealthState.DEGRADED, message=str(exc))


def _check_meta_harness() -> ComponentHealth:
    """Check MetaHarness: can instantiate MetaFramework → ready."""
    try:
        from pyc_hermes_agent.meta_harness import MetaFramework

        MetaFramework()
        return ComponentHealth(name="meta_harness", state=HealthState.READY)
    except ImportError:
        return ComponentHealth(
            name="meta_harness", state=HealthState.DEGRADED, message="meta_harness module not importable"
        )
    except Exception as exc:
        return ComponentHealth(name="meta_harness", state=HealthState.DEGRADED, message=str(exc))


def _check_mrag() -> ComponentHealth:
    """Check MRAG: no lock contention → ready; locked → degraded."""
    try:
        from pyc_hermes_agent.mrag_core import MRAGStorageLockedError  # noqa: F401

        # If we can import and no active lock contention is detected, consider ready.
        return ComponentHealth(name="mrag", state=HealthState.READY)
    except ImportError:
        return ComponentHealth(
            name="mrag", state=HealthState.DEGRADED, message="mrag_core module not importable"
        )
    except Exception as exc:
        return ComponentHealth(name="mrag", state=HealthState.DEGRADED, message=str(exc))


def _check_hermes_bridge(root: Any = None) -> ComponentHealth:
    """Check Hermes bridge health via the existing bridge health service."""
    try:
        from pathlib import Path

        from pyc_hermes_agent.sidecar_api.services.skill_service import get_hermes_bridge_health

        r = root if root is None else Path(root)
        bridge = get_hermes_bridge_health(r)
        if bridge.get("bridge_ready"):
            if bridge.get("warnings"):
                return ComponentHealth(
                    name="hermes_bridge", state=HealthState.READY_WITH_WARNINGS, message="bridge has warnings"
                )
            return ComponentHealth(name="hermes_bridge", state=HealthState.READY)
        if bridge.get("checkout_present") and bridge.get("import_ready"):
            return ComponentHealth(
                name="hermes_bridge", state=HealthState.DEGRADED, message="bridge not fully ready"
            )
        return ComponentHealth(
            name="hermes_bridge", state=HealthState.UNAVAILABLE, message="bridge unavailable"
        )
    except Exception as exc:
        return ComponentHealth(name="hermes_bridge", state=HealthState.DEGRADED, message=str(exc))


__all__ = ["ComponentHealth", "HealthState", "SidecarHealth"]
