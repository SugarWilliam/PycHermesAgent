"""Skill listing and Hermes facade service functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from pyc_hermes_agent.hermes_engine import HermesFacade
from pyc_hermes_agent.hermes_engine.skill_context import SKILLS_RUNTIME_POLICY
from pyc_hermes_agent.hermes_engine.skills import SkillRegistry, register_builtin_skills
from pyc_hermes_agent.llm_gateway import load_skill_metadata
from pyc_hermes_agent.sidecar_api.services.common import _repo_root, _serialize


# Module-level singleton registry with builtins pre-registered.
_skill_registry = SkillRegistry()
register_builtin_skills(_skill_registry)


def get_skill_registry() -> SkillRegistry:
    """Return the singleton skill registry."""
    return _skill_registry


def list_builtin_skills() -> List[Dict[str, Any]]:
    """List all builtin skills with activation state."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "category": s.category,
            "description": s.description,
            "active": s.active,
        }
        for s in _skill_registry.list_all()
    ]


def activate_skill(skill_id: str) -> Dict[str, Any]:
    """Activate a builtin skill. Returns status."""
    found = _skill_registry.activate(skill_id)
    if not found:
        raise KeyError(f"Skill not found: {skill_id}")
    return {"id": skill_id, "active": True}


def deactivate_skill(skill_id: str) -> Dict[str, Any]:
    """Deactivate a builtin skill. Returns status."""
    found = _skill_registry.deactivate(skill_id)
    if not found:
        raise KeyError(f"Skill not found: {skill_id}")
    return {"id": skill_id, "active": False}


def _get_hermes_facade(root: Path | None = None) -> HermesFacade:
    base = root or _repo_root()
    return HermesFacade(root=base)


def list_skills(root: Path | None = None) -> List[Dict[str, Any]]:
    base = root or _repo_root()
    items: List[Dict[str, Any]] = []
    for skill in load_skill_metadata(base):
        mtime_ns = skill.path.stat().st_mtime_ns
        category = skill.metadata.get("category", "prompt")
        items.append(
            {
                "id": skill.name,
                "name": skill.name,
                "description": skill.description,
                "category": category,
                "active": False,
                "source_kind": skill.skill_origin,
                "path": str(skill.path),
                "license": skill.license,
                "compatibility": skill.compatibility,
                "metadata": skill.metadata,
                "runtime": {
                    "policy": dict(SKILLS_RUNTIME_POLICY),
                    "source": {
                        "kind": "SKILL.md",
                        "path": str(skill.path),
                        "mtime_ns": mtime_ns,
                    },
                },
            }
        )
    return items


def get_hermes_capability_snapshot(root: Path | None = None) -> Dict[str, Any]:
    snapshot = _get_hermes_facade(root).get_capability_snapshot()
    return _serialize(snapshot)


def get_hermes_sessions_snapshot(root: Path | None = None) -> Dict[str, Any]:
    return _serialize(_get_hermes_facade(root).get_sessions_snapshot())


def get_hermes_memory_snapshot(root: Path | None = None) -> Dict[str, Any]:
    return _serialize(_get_hermes_facade(root).get_memory_snapshot())


def get_hermes_skills_snapshot(root: Path | None = None) -> Dict[str, Any]:
    return _serialize(_get_hermes_facade(root).get_skills_snapshot())


def get_hermes_tools_snapshot(root: Path | None = None) -> Dict[str, Any]:
    return _serialize(_get_hermes_facade(root).get_tools_snapshot())


def get_hermes_bridge_health(root: Path | None = None) -> Dict[str, Any]:
    facade = _get_hermes_facade(root)
    capability = facade.get_capability_snapshot()
    sessions = facade.get_sessions_snapshot()
    memory = facade.get_memory_snapshot()
    skills = facade.get_skills_snapshot()
    tools = facade.get_tools_snapshot()

    surfaces = {
        "sessions": sessions.integration,
        "memory": memory.integration,
        "skills": skills.integration,
        "tools": tools.integration,
    }
    bridged = [name for name, integration in surfaces.items() if integration.bridge_ready]
    blocked = [name for name, integration in surfaces.items() if integration.status == "blocked"]
    warnings: List[str] = []
    warnings.extend(capability.warnings)
    for integration in surfaces.values():
        warnings.extend(integration.warnings)

    return {
        "upstream_root": capability.upstream_root,
        "checkout_present": capability.checkout_present,
        "detected_commit": capability.detected_commit,
        "worktree_state": capability.worktree_state,
        "import_ready": capability.import_ready,
        "bridge_ready": capability.import_ready and len(bridged) == len(surfaces),
        "bridged_surfaces": sorted(bridged),
        "blocked_surfaces": sorted(blocked),
        "surface_count": len(surfaces),
        "bridged_count": len(bridged),
        "surfaces": {
            name: {
                "surface": integration.surface,
                "integration_mode": integration.integration_mode,
                "status": integration.status,
                "bridge_ready": integration.bridge_ready,
                "placeholder": integration.placeholder,
                "checkout_import_ready": integration.checkout_import_ready,
                "worktree_state": integration.worktree_state,
                "discovered_count": integration.discovered_count,
                "warnings": integration.warnings,
            }
            for name, integration in surfaces.items()
        },
        "warnings": sorted(dict.fromkeys(warnings)),
    }
