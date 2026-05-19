"""Module-level constants, specs, and placeholder declarations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _coerce_runtime_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value, 10)
        except ValueError:
            return default
    return default


@dataclass(frozen=True, slots=True)
class _SurfaceSpec:
    id: str
    kind: str
    relative_path: str
    required: bool = False


@dataclass(frozen=True, slots=True)
class _PlaceholderSpec:
    surface: str
    required_surfaces: tuple[str, ...]
    source_paths: tuple[str, ...]
    entrypoints: tuple[str, ...]
    planned_operations: tuple[str, ...]
    discovery_patterns: tuple[str, ...] = ()


_DEFAULT_UPSTREAM_RELATIVE = Path("upstream") / "hermes-agent"
_SURFACE_SPECS = (
    _SurfaceSpec("hermes.agent_loop", "orchestration", "run_agent.py", required=True),
    _SurfaceSpec("hermes.tool_dispatch", "tool-loop", "model_tools.py", required=True),
    _SurfaceSpec("hermes.tool_registry", "tool-registry", "tools/registry.py", required=True),
    _SurfaceSpec("hermes.sessions", "session-store", "hermes_state.py", required=True),
    _SurfaceSpec("hermes.memory", "memory", "agent/memory_manager.py"),
    _SurfaceSpec("hermes.skills", "skills", "agent/skill_commands.py"),
    _SurfaceSpec("hermes.cli", "cli", "cli.py"),
    _SurfaceSpec("hermes.gateway", "gateway", "gateway/run.py"),
)
_SESSIONS_PLACEHOLDER = _PlaceholderSpec(
    surface="sessions",
    required_surfaces=("hermes.sessions",),
    source_paths=("hermes_state.py",),
    entrypoints=("SessionDB", "format_session_db_unavailable"),
    planned_operations=("list", "resume", "search"),
)
_MEMORY_PLACEHOLDER = _PlaceholderSpec(
    surface="memory",
    required_surfaces=("hermes.memory",),
    source_paths=("agent/memory_manager.py",),
    entrypoints=("MemoryManager", "sanitize_context", "StreamingContextScrubber"),
    planned_operations=("prefetch", "sync", "build_prompt"),
    discovery_patterns=("plugins/memory/*/__init__.py",),
)
_SKILLS_PLACEHOLDER = _PlaceholderSpec(
    surface="skills",
    required_surfaces=("hermes.skills",),
    source_paths=("agent/skill_commands.py",),
    entrypoints=("_load_skill_payload", "get_skill_commands"),
    planned_operations=("list", "load", "invoke"),
    discovery_patterns=(
        "skills/*/SKILL.md",
        "skills/*/*/SKILL.md",
        "optional-skills/*/SKILL.md",
        "optional-skills/*/*/SKILL.md",
    ),
)
_TOOLS_PLACEHOLDER = _PlaceholderSpec(
    surface="tools",
    required_surfaces=("hermes.tool_dispatch", "hermes.tool_registry"),
    source_paths=("model_tools.py", "tools/registry.py"),
    entrypoints=("discover_builtin_tools", "get_tool_definitions", "handle_function_call"),
    planned_operations=("discover", "describe", "dispatch"),
    discovery_patterns=("tools/*.py", "tools/**/*.py"),
)
_SESSION_OPERATIONS = (
    ("create_session", "lifecycle"),
    ("end_session", "lifecycle"),
    ("reopen_session", "lifecycle"),
    ("get_session", "read"),
    ("resolve_session_id", "read"),
    ("list_sessions_rich", "browse"),
    ("resolve_resume_session_id", "resume"),
    ("search_messages", "search"),
    ("search_sessions", "search"),
    ("set_session_title", "title"),
    ("get_session_title", "title"),
    ("get_session_by_title", "title"),
    ("resolve_session_by_title", "title"),
    ("request_handoff", "handoff"),
    ("get_handoff_state", "handoff"),
    ("list_pending_handoffs", "handoff"),
    ("claim_handoff", "handoff"),
    ("complete_handoff", "handoff"),
    ("fail_handoff", "handoff"),
)
_TOOL_OPERATIONS = (
    ("discover_builtin_tools", "discovery"),
    ("discover_plugins", "plugin-discovery"),
    ("get_tool_definitions", "schema"),
    ("handle_function_call", "dispatch"),
    ("get_all_tool_names", "introspection"),
    ("get_toolset_for_tool", "introspection"),
    ("get_available_toolsets", "introspection"),
    ("check_toolset_requirements", "requirements"),
    ("check_tool_availability", "requirements"),
    ("resolve_toolset", "toolset-resolution"),
    ("validate_toolset", "toolset-resolution"),
)
_TOOL_DISCOVERY_PATTERNS = ("tools/*.py", "tools/**/*.py")
_MEMORY_OPERATIONS = (
    ("add_provider", "registration"),
    ("get_provider", "registration"),
    ("build_system_prompt", "prompt"),
    ("prefetch_all", "prefetch"),
    ("queue_prefetch_all", "prefetch"),
    ("sync_all", "sync"),
    ("get_all_tool_schemas", "tools"),
    ("route_tool_call", "tools"),
    ("shutdown_all", "lifecycle"),
)
_MEMORY_PROVIDER_HOOKS = (
    "is_available",
    "initialize",
    "system_prompt_block",
    "prefetch",
    "queue_prefetch",
    "sync_turn",
    "get_tool_schemas",
    "handle_tool_call",
    "shutdown",
    "on_turn_start",
    "on_session_end",
    "on_session_switch",
    "on_pre_compress",
    "on_delegation",
    "get_config_schema",
    "save_config",
    "on_memory_write",
)
