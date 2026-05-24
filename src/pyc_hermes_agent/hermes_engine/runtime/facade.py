"""The main HermesFacade class and module-level convenience functions."""

from __future__ import annotations

from pathlib import Path

from pyc_hermes_agent.contracts import (
    HermesMemoryManagerDescriptor,
    HermesMemorySnapshot,
    HermesRuntimeSnapshot,
    HermesSessionsSnapshot,
    HermesSessionStoreDescriptor,
    HermesSkillsSnapshot,
    HermesToolRegistryDescriptor,
    HermesToolsSnapshot,
)

from .constants import (
    _MEMORY_PLACEHOLDER,
    _SESSIONS_PLACEHOLDER,
    _SKILLS_PLACEHOLDER,
    _SURFACE_SPECS,
    _TOOLS_PLACEHOLDER,
)
from .discovery import (
    _build_placeholder_snapshot,
    _build_skill_descriptor,
    _build_surface,
    _discover_skill_paths,
    _discover_skill_roots,
    _unique,
)
from .git_probe import (
    _has_git_index_lock,
    _probe_memory_runtime,
    _probe_sessions_runtime,
    _probe_skills_runtime,
    _probe_tools_runtime,
    _read_head_commit,
    _read_worktree_state,
    _resolve_git_dir,
    _resolve_upstream_root,
)
from .bridges import (
    _bridge_memory_integration,
    _bridge_sessions_integration,
    _bridge_skills_integration,
    _bridge_tools_integration,
)
from .builders import (
    _build_memory_manager_descriptor,
    _build_memory_operations,
    _build_memory_provider_descriptors,
    _build_session_operations,
    _build_session_store_descriptor,
    _build_tool_descriptors,
    _build_tool_operations,
    _build_tool_registry_descriptor,
)


class HermesFacade:
    """Read-only seam over the vendored Hermes checkout."""

    def __init__(self, root: Path | None = None, upstream_root: Path | None = None) -> None:
        self._root = root
        self._upstream_root = upstream_root
        self._capability_snapshot: HermesRuntimeSnapshot | None = None
        self._sessions_snapshot: HermesSessionsSnapshot | None = None
        self._memory_snapshot: HermesMemorySnapshot | None = None
        self._skills_snapshot: HermesSkillsSnapshot | None = None
        self._tools_snapshot: HermesToolsSnapshot | None = None

    def get_capability_snapshot(self) -> HermesRuntimeSnapshot:
        if self._capability_snapshot is not None:
            return self._capability_snapshot

        upstream_root = _resolve_upstream_root(self._root, self._upstream_root)
        checkout_present = upstream_root.exists()
        git_dir = _resolve_git_dir(upstream_root) if checkout_present else None
        detected_commit = _read_head_commit(git_dir)
        worktree_state = _read_worktree_state(upstream_root, git_dir)
        surfaces = [_build_surface(spec, upstream_root) for spec in _SURFACE_SPECS]

        missing_required = [surface.id for surface in surfaces if surface.required and not surface.available]
        import_ready = checkout_present and not missing_required and worktree_state != "inconsistent"

        warnings: list[str] = []
        if not checkout_present:
            warnings.append("Hermes upstream checkout is missing.")
        if checkout_present and git_dir is None:
            warnings.append("Hermes upstream checkout does not expose Git metadata.")
        if checkout_present and not detected_commit:
            warnings.append("Hermes upstream checkout does not resolve a HEAD commit.")
        if _has_git_index_lock(git_dir):
            warnings.append("Hermes upstream Git index is locked.")
        if missing_required:
            warnings.append(f"Missing required Hermes surfaces: {', '.join(missing_required)}.")
        if worktree_state == "dirty":
            warnings.append("Hermes upstream worktree has pending changes.")
        if worktree_state == "inconsistent":
            warnings.append("Hermes upstream worktree mixes tracked deletions with untracked paths.")

        self._capability_snapshot = HermesRuntimeSnapshot(
            upstream_root=str(upstream_root),
            checkout_present=checkout_present,
            git_dir_present=git_dir is not None,
            detected_commit=detected_commit,
            worktree_state=worktree_state,
            import_ready=import_ready,
            surfaces=surfaces,
            warnings=warnings,
        )
        return self._capability_snapshot

    def get_sessions_snapshot(self) -> HermesSessionsSnapshot:
        if self._sessions_snapshot is not None:
            return self._sessions_snapshot

        runtime_snapshot = self.get_capability_snapshot()
        integration = _build_placeholder_snapshot(_SESSIONS_PLACEHOLDER, runtime_snapshot)
        upstream_root = Path(runtime_snapshot.upstream_root)
        store = _build_session_store_descriptor(upstream_root) if runtime_snapshot.checkout_present else HermesSessionStoreDescriptor()
        operations = _build_session_operations(upstream_root) if runtime_snapshot.checkout_present else []
        runtime_result: dict[str, object] | None = None
        runtime_warnings: list[str] = []
        if runtime_snapshot.import_ready:
            runtime_result, runtime_warnings = _probe_sessions_runtime(upstream_root)
            if runtime_result is not None:
                integration = _bridge_sessions_integration(integration, runtime_result, operations)
        warnings: list[str] = []
        if not store.schema_version_number and runtime_snapshot.checkout_present:
            warnings.append("Hermes session store schema version was not detected.")
        if not store.tables and runtime_snapshot.checkout_present:
            warnings.append("Hermes session store tables were not detected.")
        warnings.extend(runtime_warnings)
        self._sessions_snapshot = HermesSessionsSnapshot(
            integration=integration,
            store=store,
            entrypoints=integration.detected_entrypoints,
            operations=operations,
            warnings=_unique(warnings),
        )
        return self._sessions_snapshot

    def get_memory_snapshot(self) -> HermesMemorySnapshot:
        if self._memory_snapshot is not None:
            return self._memory_snapshot

        runtime_snapshot = self.get_capability_snapshot()
        integration = _build_placeholder_snapshot(_MEMORY_PLACEHOLDER, runtime_snapshot)
        upstream_root = Path(runtime_snapshot.upstream_root)
        manager = _build_memory_manager_descriptor(upstream_root) if runtime_snapshot.checkout_present else HermesMemoryManagerDescriptor()
        operations = _build_memory_operations(upstream_root) if runtime_snapshot.checkout_present else []
        providers = _build_memory_provider_descriptors(upstream_root) if runtime_snapshot.checkout_present else []
        runtime_result: dict[str, object] | None = None
        runtime_warnings: list[str] = []
        if runtime_snapshot.import_ready:
            runtime_result, runtime_warnings = _probe_memory_runtime(upstream_root)
            if runtime_result is not None:
                integration = _bridge_memory_integration(integration, runtime_result, operations, providers)
        warnings = _unique([f"Memory provider metadata issue for {provider.path}: {provider.parse_error}" for provider in providers if provider.parse_error])
        warnings.extend(runtime_warnings)
        if runtime_snapshot.checkout_present and not providers:
            warnings.append("No Hermes memory providers were discovered from vendored sources.")
        self._memory_snapshot = HermesMemorySnapshot(
            integration=integration,
            manager=manager,
            operations=operations,
            providers=providers,
            warnings=_unique(warnings),
        )
        return self._memory_snapshot

    def get_skills_snapshot(self) -> HermesSkillsSnapshot:
        if self._skills_snapshot is not None:
            return self._skills_snapshot

        runtime_snapshot = self.get_capability_snapshot()
        integration = _build_placeholder_snapshot(_SKILLS_PLACEHOLDER, runtime_snapshot)
        upstream_root = Path(runtime_snapshot.upstream_root)
        skill_paths = _discover_skill_paths(upstream_root) if runtime_snapshot.checkout_present else []
        skills = [_build_skill_descriptor(skill_path, upstream_root) for skill_path in skill_paths]
        runtime_result: dict[str, object] | None = None
        runtime_warnings: list[str] = []
        if runtime_snapshot.import_ready:
            runtime_result, runtime_warnings = _probe_skills_runtime(upstream_root)
            if runtime_result is not None:
                integration = _bridge_skills_integration(integration, runtime_result, skills)
        warnings = _unique([f"Skill metadata issue for {skill.path}: {skill.parse_error}" for skill in skills if skill.parse_error])
        warnings.extend(runtime_warnings)
        self._skills_snapshot = HermesSkillsSnapshot(
            integration=integration,
            discovery_roots=_discover_skill_roots(upstream_root) if runtime_snapshot.checkout_present else [],
            skills=skills,
            warnings=_unique(warnings),
        )
        return self._skills_snapshot

    def get_tools_snapshot(self) -> HermesToolsSnapshot:
        if self._tools_snapshot is not None:
            return self._tools_snapshot

        runtime_snapshot = self.get_capability_snapshot()
        integration = _build_placeholder_snapshot(_TOOLS_PLACEHOLDER, runtime_snapshot)
        upstream_root = Path(runtime_snapshot.upstream_root)
        registry = _build_tool_registry_descriptor(upstream_root) if runtime_snapshot.checkout_present else HermesToolRegistryDescriptor()
        operations = _build_tool_operations(upstream_root) if runtime_snapshot.checkout_present else []
        tools = _build_tool_descriptors(upstream_root) if runtime_snapshot.checkout_present else []
        runtime_result: dict[str, object] | None = None
        runtime_warnings: list[str] = []
        if runtime_snapshot.import_ready:
            runtime_result, runtime_warnings = _probe_tools_runtime(upstream_root)
            if runtime_result is not None:
                integration = _bridge_tools_integration(integration, runtime_result, operations, tools)
        warnings = _unique([f"Tool metadata issue for {tool.path}: {tool.parse_error}" for tool in tools if tool.parse_error])
        warnings.extend(runtime_warnings)
        if runtime_snapshot.checkout_present and not tools:
            warnings.append("No Hermes builtin tools were discovered from vendored sources.")
        self._tools_snapshot = HermesToolsSnapshot(
            integration=integration,
            registry=registry,
            operations=operations,
            tools=tools,
            warnings=_unique(warnings),
        )
        return self._tools_snapshot


def get_capability_snapshot(root: Path | None = None, upstream_root: Path | None = None) -> HermesRuntimeSnapshot:
    return HermesFacade(root=root, upstream_root=upstream_root).get_capability_snapshot()


def get_sessions_snapshot(root: Path | None = None, upstream_root: Path | None = None) -> HermesSessionsSnapshot:
    return HermesFacade(root=root, upstream_root=upstream_root).get_sessions_snapshot()


def get_memory_snapshot(root: Path | None = None, upstream_root: Path | None = None) -> HermesMemorySnapshot:
    return HermesFacade(root=root, upstream_root=upstream_root).get_memory_snapshot()


def get_skills_snapshot(root: Path | None = None, upstream_root: Path | None = None) -> HermesSkillsSnapshot:
    return HermesFacade(root=root, upstream_root=upstream_root).get_skills_snapshot()


def get_tools_snapshot(root: Path | None = None, upstream_root: Path | None = None) -> HermesToolsSnapshot:
    return HermesFacade(root=root, upstream_root=upstream_root).get_tools_snapshot()
