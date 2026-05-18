"""Discovery-first Hermes integration seam."""

from __future__ import annotations

import ast
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from pyc_hermes_agent.contracts import (
    HermesIntegrationSnapshot,
    HermesMemoryManagerDescriptor,
    HermesMemoryOperation,
    HermesMemoryProviderDescriptor,
    HermesMemorySnapshot,
    HermesRuntimeSnapshot,
    HermesSessionOperation,
    HermesSessionsSnapshot,
    HermesSessionStoreDescriptor,
    HermesSkillDescriptor,
    HermesSkillsSnapshot,
    HermesSurface,
    HermesToolDescriptor,
    HermesToolOperation,
    HermesToolRegistryDescriptor,
    HermesToolsSnapshot,
)


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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_upstream_root(root: Path | None = None, upstream_root: Path | None = None) -> Path:
    if upstream_root is not None:
        return upstream_root
    base = root or _repo_root()
    return base / _DEFAULT_UPSTREAM_RELATIVE


def _resolve_git_dir(repo_root: Path) -> Path | None:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git
    if not dot_git.is_file():
        return None

    try:
        raw = dot_git.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw.lower().startswith("gitdir:"):
        return None

    git_dir = Path(raw.split(":", 1)[1].strip())
    if not git_dir.is_absolute():
        git_dir = repo_root / git_dir
    return git_dir.resolve()


def _read_packed_ref(git_dir: Path, ref_name: str) -> str:
    packed_refs = git_dir / "packed-refs"
    if not packed_refs.exists():
        return ""

    try:
        lines = packed_refs.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""

    for line in lines:
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        commit, _, ref = line.partition(" ")
        if ref.strip() == ref_name:
            return commit.strip()
    return ""


def _read_head_commit(git_dir: Path | None) -> str:
    if git_dir is None:
        return ""

    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return ""

    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not head:
        return ""
    if len(head) == 40 and all(char in "0123456789abcdef" for char in head.lower()):
        return head
    if not head.startswith("ref:"):
        return ""

    ref_name = head.split(":", 1)[1].strip()
    ref_path = git_dir / ref_name
    if ref_path.exists():
        try:
            return ref_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return _read_packed_ref(git_dir, ref_name)


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json_line(text: str) -> dict[str, object] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _run_upstream_json_probe(
    upstream_root: Path,
    script: str,
    *,
    probe_name: str,
    env_updates: dict[str, str] | None = None,
) -> tuple[dict[str, object] | None, list[str]]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    if env_updates:
        env.update(env_updates)

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(upstream_root),
            env=env,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, [f"Hermes {probe_name} runtime probe failed: {exc}."]

    payload = _read_json_line(result.stdout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
        return None, [f"Hermes {probe_name} runtime probe failed: {detail}."]
    if payload is None:
        detail = result.stdout.strip() or result.stderr.strip() or "missing JSON payload"
        return None, [f"Hermes {probe_name} runtime probe failed: {detail}."]
    if payload.get("success") is not True:
        detail = str(payload.get("error") or f"{probe_name} probe returned success=false")
        return None, [f"Hermes {probe_name} runtime probe failed: {detail}."]
    return payload, []


def _read_worktree_state(repo_root: Path, git_dir: Path | None) -> str:
    if not repo_root.exists():
        return "missing"
    if git_dir is None:
        return "unknown"

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--short", "--untracked-files=normal"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"

    if result.returncode != 0:
        return "unknown"

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return "clean"

    deleted = sum(1 for line in lines if line[:2] in {"D ", " D"})
    untracked = sum(1 for line in lines if line.startswith("?? "))
    if deleted and untracked:
        return "inconsistent"
    return "dirty"


def _has_git_index_lock(git_dir: Path | None) -> bool:
    if git_dir is None:
        return False
    return (git_dir / "index.lock").exists()


def _build_surface(spec: _SurfaceSpec, upstream_root: Path) -> HermesSurface:
    return HermesSurface(
        id=spec.id,
        kind=spec.kind,
        path=spec.relative_path,
        available=(upstream_root / spec.relative_path).exists(),
        required=spec.required,
    )


def _parse_frontmatter(text: str) -> tuple[dict[str, str], dict[str, str], str | None]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, {}, "Skill frontmatter missing."

    frontmatter: dict[str, str] = {}
    nested_metadata: dict[str, str] = {}
    in_metadata_block = False

    idx = 1
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---":
            return frontmatter, nested_metadata, None

        if in_metadata_block and line.startswith("  "):
            if ":" in line:
                key, value = line.strip().split(":", 1)
                nested_metadata[key.strip()] = value.strip()
            idx += 1
            continue

        in_metadata_block = False
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "metadata":
                in_metadata_block = True
            else:
                frontmatter[key] = value
        idx += 1

    return frontmatter, nested_metadata, "Skill frontmatter terminator missing."


def _derive_markdown_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def _literal_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_str_list(node: ast.AST) -> list[str]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return []
    values: list[str] = []
    for element in node.elts:
        value = _literal_str(element)
        if value is not None:
            values.append(value)
    return values


def _search_value(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def _surface_lookup(snapshot: HermesRuntimeSnapshot) -> dict[str, HermesSurface]:
    return {surface.id: surface for surface in snapshot.surfaces}


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _detect_entrypoints(upstream_root: Path, source_paths: tuple[str, ...], entrypoints: tuple[str, ...]) -> list[str]:
    detected: list[str] = []
    texts = [_read_text(upstream_root / relative_path) for relative_path in source_paths]
    for entrypoint in entrypoints:
        name_pattern = re.compile(rf"^\s*(?:class|def)\s+{re.escape(entrypoint)}\b", re.MULTILINE)
        if any(name_pattern.search(text) or entrypoint in text for text in texts if text):
            detected.append(entrypoint)
    return detected


def _discover_paths(upstream_root: Path, patterns: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        for path in upstream_root.glob(pattern):
            if path.is_file():
                matches.append(path.relative_to(upstream_root).as_posix())
    return sorted(_unique(matches))


def _discover_skill_paths(upstream_root: Path) -> list[Path]:
    return [upstream_root / relative_path for relative_path in _discover_paths(upstream_root, _SKILLS_PLACEHOLDER.discovery_patterns)]


def _discover_skill_roots(upstream_root: Path) -> list[str]:
    roots: list[str] = []
    for relative_path in ("skills", "optional-skills"):
        if (upstream_root / relative_path).exists():
            roots.append(relative_path)
    return roots


def _probe_skills_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    skills_tool = upstream_root / "tools" / "skills_tool.py"
    if not skills_tool.exists():
        return None, []

    script = (
        "import json, pathlib, sys;"
        "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
        "from tools.skills_tool import skills_list;"
        "result = json.loads(skills_list());"
        "payload = {"
        "'success': bool(result.get('success')),"
        "'count': result.get('count'),"
        "'skills': result.get('skills') or [],"
        "'categories': result.get('categories') or [],"
        "'error': result.get('error')"
        "};"
        "print(json.dumps(payload, ensure_ascii=False))"
    )
    return _run_upstream_json_probe(
        upstream_root,
        script,
        probe_name="skills",
        env_updates={"HERMES_HOME": str(upstream_root)},
    )


def _probe_sessions_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    hermes_state = upstream_root / "hermes_state.py"
    if not hermes_state.exists():
        return None, []

    with tempfile.TemporaryDirectory(prefix="pyc-hermes-session-probe-") as temp_dir:
        probe_db = Path(temp_dir) / "probe-state.db"
        script = (
            "import json, os, pathlib, sys;"
            "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
            "from hermes_state import DEFAULT_DB_PATH, SCHEMA_VERSION, SessionDB;"
            "db_path = pathlib.Path(os.environ['PYC_HERMES_SESSION_PROBE_DB']);"
            "db = SessionDB(db_path=db_path);"
            "session_id = 'pyc-hermes-session-probe';"
            "created = db.create_session(session_id=session_id, source='cli');"
            "session = db.get_session(session_id);"
            "listed = db.list_sessions_rich(limit=5);"
            "resolved = db.resolve_session_id(session_id);"
            "resume = db.resolve_resume_session_id(session_id);"
            "payload = {"
            "'success': True,"
            "'schema_version': SCHEMA_VERSION,"
            "'default_db_path': str(DEFAULT_DB_PATH),"
            "'db_path': str(db_path),"
            "'created': created,"
            "'get_session_ok': bool(session),"
            "'list_count': len(listed),"
            "'resolved': resolved,"
            "'resume': resume"
            "};"
            "print(json.dumps(payload, ensure_ascii=False))"
        )
        return _run_upstream_json_probe(
            upstream_root,
            script,
            probe_name="sessions",
            env_updates={
                "HERMES_HOME": temp_dir,
                "PYC_HERMES_SESSION_PROBE_DB": str(probe_db),
            },
        )


def _probe_tools_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    model_tools = upstream_root / "model_tools.py"
    if not model_tools.exists():
        return None, []

    with tempfile.TemporaryDirectory(prefix="pyc-hermes-tool-probe-") as temp_dir:
        script = (
            "import json, pathlib, sys;"
            "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
            "import model_tools;"
            "tool_names = model_tools.get_all_tool_names();"
            "toolsets = model_tools.get_available_toolsets();"
            "requirements = model_tools.check_toolset_requirements();"
            "availability = model_tools.check_tool_availability(True);"
            "payload = {"
            "'success': True,"
            "'tool_count': len(tool_names),"
            "'tool_names': tool_names[:20],"
            "'toolset_count': len(toolsets),"
            "'toolset_names': list(toolsets.keys())[:20],"
            "'requirements_count': len(requirements),"
            "'availability_tuple_len': len(availability) if isinstance(availability, tuple) else 0"
            "};"
            "print(json.dumps(payload, ensure_ascii=False))"
        )
        return _run_upstream_json_probe(
            upstream_root,
            script,
            probe_name="tools",
            env_updates={"HERMES_HOME": temp_dir},
        )


def _probe_memory_runtime(upstream_root: Path) -> tuple[dict[str, object] | None, list[str]]:
    manager_path = upstream_root / "agent" / "memory_manager.py"
    if not manager_path.exists():
        return None, []

    with tempfile.TemporaryDirectory(prefix="pyc-hermes-memory-probe-") as temp_dir:
        script = (
            "import json, pathlib, sys;"
            "sys.path.insert(0, str(pathlib.Path('.').resolve()));"
            "from agent.memory_manager import MemoryManager, StreamingContextScrubber, build_memory_context_block, sanitize_context;"
            "manager = MemoryManager();"
            "prompt = manager.build_system_prompt();"
            "prefetch = manager.prefetch_all('probe', session_id='probe-session');"
            "schemas = manager.get_all_tool_schemas();"
            "scrubber = StreamingContextScrubber();"
            "visible = scrubber.feed('probe');"
            "flushed = scrubber.flush();"
            "fenced = build_memory_context_block('memo');"
            "payload = {"
            "'success': True,"
            "'provider_count': len(manager.providers),"
            "'prompt_empty': prompt == '',"
            "'prefetch_empty': prefetch == '',"
            "'schemas_count': len(schemas),"
            "'stream_visible': visible,"
            "'stream_flushed': flushed,"
            "'fenced_has_tag': '<memory-context>' in fenced,"
            "'sanitized': sanitize_context('<memory-context>x</memory-context>')"
            "};"
            "print(json.dumps(payload, ensure_ascii=False))"
        )
        return _run_upstream_json_probe(
            upstream_root,
            script,
            probe_name="memory",
            env_updates={"HERMES_HOME": temp_dir},
        )


def _build_skill_descriptor(skill_path: Path, upstream_root: Path) -> HermesSkillDescriptor:
    relative_path = skill_path.relative_to(upstream_root).as_posix()
    parts = skill_path.relative_to(upstream_root).parts
    source = "optional" if parts and parts[0] == "optional-skills" else "bundled"
    derived_category = parts[1] if len(parts) >= 3 else ""
    descriptor_id = "/".join(parts[1:-1]) if len(parts) >= 3 else skill_path.parent.name
    text = _read_text(skill_path)
    frontmatter, metadata, parse_error = _parse_frontmatter(text)

    missing_fields: list[str] = []
    if not frontmatter.get("name"):
        missing_fields.append("name")
    if not frontmatter.get("description"):
        missing_fields.append("description")
    if missing_fields:
        parse_error = parse_error or f"Skill metadata missing required fields: {', '.join(missing_fields)}."

    return HermesSkillDescriptor(
        id=descriptor_id,
        name=frontmatter.get("name") or _derive_markdown_title(text, skill_path.parent.name),
        description=frontmatter.get("description", ""),
        path=relative_path,
        source=source,
        category=metadata.get("category") or frontmatter.get("category", derived_category),
        license=frontmatter.get("license"),
        compatibility=frontmatter.get("compatibility"),
        metadata=metadata,
        loadable=parse_error is None,
        parse_error=parse_error,
    )


def _build_skills_runtime_sample_paths(runtime_skills: list[object], skills: list[HermesSkillDescriptor]) -> list[str]:
    by_name_and_category: dict[tuple[str, str], str] = {}
    by_name: dict[str, str] = {}

    for skill in skills:
        if skill.source != "bundled":
            continue
        key = (skill.name, skill.category or "")
        by_name_and_category.setdefault(key, skill.path)
        by_name.setdefault(skill.name, skill.path)

    sample_paths: list[str] = []
    for item in runtime_skills:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        category = str(item.get("category") or "").strip()
        if not name:
            continue
        resolved_path = by_name_and_category.get((name, category)) or by_name.get(name)
        sample_paths.append(resolved_path or name)
    return _unique(sample_paths)


def _bridge_sessions_integration(
    integration: HermesIntegrationSnapshot,
    runtime_result: dict[str, object],
    operations: list[HermesSessionOperation],
) -> HermesIntegrationSnapshot:
    warnings = list(integration.warnings)
    expected_ok = all(
        [
            runtime_result.get("get_session_ok") is True,
            isinstance(runtime_result.get("list_count"), int),
            runtime_result.get("resolved"),
            runtime_result.get("resume"),
        ]
    )
    if not expected_ok:
        warnings.append("Hermes sessions runtime probe returned incomplete session operation coverage.")

    sample_paths = list(integration.sample_paths)
    db_path = runtime_result.get("default_db_path")
    if isinstance(db_path, str) and db_path:
        sample_paths = [db_path]

    available_operations = [operation.name for operation in operations if operation.available]

    return replace(
        integration,
        integration_mode="subprocess-readonly",
        status="bridged",
        placeholder=False,
        bridge_ready=True,
        detected_entrypoints=_unique([*integration.detected_entrypoints, "SessionDB"]),
        planned_operations=_unique([*integration.planned_operations, *available_operations]),
        discovered_count=_coerce_runtime_int(runtime_result.get("list_count"), default=0),
        sample_paths=sample_paths[:20],
        warnings=_unique(warnings),
    )


def _build_tools_runtime_sample_paths(runtime_tool_names: list[object], tools: list[HermesToolDescriptor]) -> list[str]:
    by_name = {tool.name: tool.path for tool in tools}
    sample_paths: list[str] = []
    for item in runtime_tool_names:
        if not isinstance(item, str) or not item.strip():
            continue
        sample_paths.append(by_name.get(item, item))
    return _unique(sample_paths)


def _bridge_tools_integration(
    integration: HermesIntegrationSnapshot,
    runtime_result: dict[str, object],
    operations: list[HermesToolOperation],
    tools: list[HermesToolDescriptor],
) -> HermesIntegrationSnapshot:
    warnings = list(integration.warnings)
    availability_tuple_len = runtime_result.get("availability_tuple_len")
    if availability_tuple_len != 2:
        warnings.append("Hermes tools runtime probe returned an unexpected availability tuple shape.")

    runtime_tool_names = runtime_result.get("tool_names")
    if not isinstance(runtime_tool_names, list):
        runtime_tool_names = []

    runtime_toolset_names = runtime_result.get("toolset_names")
    if not isinstance(runtime_toolset_names, list):
        runtime_toolset_names = []

    available_operations = [operation.name for operation in operations if operation.available]

    return replace(
        integration,
        integration_mode="subprocess-readonly",
        status="bridged",
        placeholder=False,
        bridge_ready=True,
        detected_entrypoints=_unique([*integration.detected_entrypoints, "get_all_tool_names", "get_available_toolsets"]),
        planned_operations=_unique([*integration.planned_operations, *available_operations]),
        discovered_count=_coerce_runtime_int(runtime_result.get("tool_count"), default=0),
        sample_paths=_build_tools_runtime_sample_paths(runtime_tool_names, tools)[:20]
        or _unique([*integration.sample_paths, *[str(item) for item in runtime_toolset_names]])[:20],
        warnings=_unique(warnings),
    )


def _bridge_memory_integration(
    integration: HermesIntegrationSnapshot,
    runtime_result: dict[str, object],
    operations: list[HermesMemoryOperation],
    providers: list[HermesMemoryProviderDescriptor],
) -> HermesIntegrationSnapshot:
    warnings = list(integration.warnings)
    if runtime_result.get("fenced_has_tag") is not True:
        warnings.append("Hermes memory runtime probe did not confirm fenced context output.")
    if runtime_result.get("sanitized") != "":
        warnings.append("Hermes memory runtime probe did not confirm context sanitization.")

    available_operations = [operation.name for operation in operations if operation.available]
    sample_paths = list(integration.sample_paths)
    runtime_provider_count = runtime_result.get("provider_count")
    if isinstance(runtime_provider_count, int) and runtime_provider_count == 0:
        sample_paths = _unique([*sample_paths, "agent/memory_manager.py"])
    elif providers:
        sample_paths = _unique([*sample_paths, *[provider.path for provider in providers[:5]]])

    return replace(
        integration,
        integration_mode="subprocess-readonly",
        status="bridged",
        placeholder=False,
        bridge_ready=True,
        detected_entrypoints=_unique([*integration.detected_entrypoints, "MemoryManager", "build_memory_context_block"]),
        planned_operations=_unique([*integration.planned_operations, *available_operations]),
        discovered_count=_coerce_runtime_int(runtime_result.get("provider_count"), default=0),
        sample_paths=sample_paths[:20],
        warnings=_unique(warnings),
    )


def _bridge_skills_integration(
    integration: HermesIntegrationSnapshot,
    runtime_result: dict[str, object],
    skills: list[HermesSkillDescriptor],
) -> HermesIntegrationSnapshot:
    runtime_skills = runtime_result.get("skills")
    if not isinstance(runtime_skills, list):
        runtime_skills = []

    runtime_count = runtime_result.get("count")
    if not isinstance(runtime_count, int) or runtime_count < 0:
        runtime_count = len(runtime_skills)

    warnings = list(integration.warnings)
    if runtime_count != len(skills):
        warnings.append(
            "Hermes skills runtime probe validates the active skill listing; packaged optional or "
            "platform-gated skills may remain metadata-only in this snapshot."
        )

    return replace(
        integration,
        integration_mode="subprocess-readonly",
        status="bridged",
        placeholder=False,
        bridge_ready=True,
        detected_entrypoints=_unique([*integration.detected_entrypoints, "skills_list"]),
        discovered_count=runtime_count,
        sample_paths=_build_skills_runtime_sample_paths(runtime_skills, skills)[:20] or integration.sample_paths,
        warnings=_unique(warnings),
    )


def _extract_session_schema_sql(upstream_root: Path) -> str:
    text = _read_text(upstream_root / "hermes_state.py")
    match = re.search(r'SCHEMA_SQL = """(.*?)"""', text, re.DOTALL)
    if not match:
        return ""
    return match.group(1)


def _extract_session_fts_sql(upstream_root: Path) -> str:
    text = _read_text(upstream_root / "hermes_state.py")
    standard_match = re.search(r'FTS_SQL = """(.*?)"""', text, re.DOTALL)
    trigram_match = re.search(r'FTS_TRIGRAM_SQL = """(.*?)"""', text, re.DOTALL)
    standard = standard_match.group(1) if standard_match else ""
    trigram = trigram_match.group(1) if trigram_match else ""
    return "\n".join(part for part in (standard, trigram) if part)


def _extract_session_schema_version(upstream_root: Path) -> int | None:
    text = _read_text(upstream_root / "hermes_state.py")
    raw = _search_value(r'^SCHEMA_VERSION\s*=\s*(\d+)', text)
    return int(raw) if raw else None


def _extract_session_db_path_hint(upstream_root: Path) -> str:
    text = _read_text(upstream_root / "hermes_state.py")
    return _search_value(r'^DEFAULT_DB_PATH\s*=\s*(.+)$', text)


def _extract_sql_objects(schema_sql: str, object_type: str) -> list[str]:
    if not schema_sql:
        return []
    pattern = re.compile(rf'CREATE\s+(?:UNIQUE\s+)?{object_type}\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_]+)', re.IGNORECASE)
    return _unique([match.group(1) for match in pattern.finditer(schema_sql)])


def _build_session_store_descriptor(upstream_root: Path) -> HermesSessionStoreDescriptor:
    schema_sql = _extract_session_schema_sql(upstream_root)
    fts_sql = _extract_session_fts_sql(upstream_root)
    combined_sql = "\n".join(part for part in (schema_sql, fts_sql) if part)
    features: list[str] = []
    if "journal_mode=WAL" in _read_text(upstream_root / "hermes_state.py"):
        features.append("wal")
    if "messages_fts" in combined_sql:
        features.append("fts5")
    if "messages_fts_trigram" in combined_sql:
        features.append("fts5-trigram")
    if "parent_session_id" in schema_sql:
        features.append("session-lineage")
    if "handoff_state" in schema_sql:
        features.append("handoff-state")
    return HermesSessionStoreDescriptor(
        path_hint=_extract_session_db_path_hint(upstream_root),
        schema_version_number=_extract_session_schema_version(upstream_root),
        backend="sqlite",
        tables=_extract_sql_objects(combined_sql, "TABLE") + _extract_sql_objects(combined_sql, "VIRTUAL TABLE"),
        indexes=_extract_sql_objects(combined_sql, "INDEX"),
        features=_unique(features),
    )


def _build_session_operations(upstream_root: Path) -> list[HermesSessionOperation]:
    text = _read_text(upstream_root / "hermes_state.py")
    operations: list[HermesSessionOperation] = []
    for name, category in _SESSION_OPERATIONS:
        pattern = re.compile(rf'^\s*def\s+{re.escape(name)}\b', re.MULTILINE)
        operations.append(
            HermesSessionOperation(
                name=name,
                category=category,
                available=bool(pattern.search(text)),
            )
        )
    return operations


def _extract_model_tools_public_api(upstream_root: Path) -> list[str]:
    text = _read_text(upstream_root / "model_tools.py")
    names: list[str] = []
    for name, _ in _TOOL_OPERATIONS:
        pattern = re.compile(rf'^\s*def\s+{re.escape(name)}\b', re.MULTILINE)
        if pattern.search(text):
            names.append(name)
    return names


def _extract_legacy_toolset_aliases(upstream_root: Path) -> list[str]:
    text = _read_text(upstream_root / "model_tools.py")
    match = re.search(r'_LEGACY_TOOLSET_MAP\s*=\s*\{(.*?)\n\}', text, re.DOTALL)
    if not match:
        return []
    return sorted(_unique(re.findall(r'["\']([^"\']+)["\']\s*:', match.group(1))))


def _build_tool_registry_descriptor(upstream_root: Path) -> HermesToolRegistryDescriptor:
    features: list[str] = []
    model_tools_text = _read_text(upstream_root / "model_tools.py")
    registry_text = _read_text(upstream_root / "tools" / "registry.py")
    if "discover_builtin_tools()" in model_tools_text:
        features.append("builtin-discovery")
    if "discover_plugins()" in model_tools_text:
        features.append("plugin-discovery")
    if "_LEGACY_TOOLSET_MAP" in model_tools_text:
        features.append("legacy-toolset-aliases")
    if "registry.register" in registry_text:
        features.append("registry-register")
    if "requires_env" in registry_text:
        features.append("env-requirements")
    return HermesToolRegistryDescriptor(
        registry_path="tools/registry.py",
        toolsets_path="toolsets.py",
        discovery_roots=[path for path in ("tools", "plugins") if (upstream_root / path).exists()],
        legacy_toolset_aliases=_extract_legacy_toolset_aliases(upstream_root),
        public_api=_extract_model_tools_public_api(upstream_root),
        features=_unique(features),
    )


def _build_tool_operations(upstream_root: Path) -> list[HermesToolOperation]:
    model_tools_text = _read_text(upstream_root / "model_tools.py")
    toolsets_text = _read_text(upstream_root / "toolsets.py")
    operations: list[HermesToolOperation] = []
    for name, category in _TOOL_OPERATIONS:
        haystack = model_tools_text if name not in {"resolve_toolset", "validate_toolset"} else toolsets_text
        pattern = re.compile(rf'^\s*def\s+{re.escape(name)}\b', re.MULTILINE)
        operations.append(
            HermesToolOperation(
                name=name,
                category=category,
                available=bool(pattern.search(haystack) or f"{name}(" in haystack),
            )
        )
    return operations


def _extract_toolset_hints(tool_name: str, toolsets_text: str) -> list[str]:
    hints: list[str] = []
    simple_pattern = re.compile(
        rf'''["\']([^"\']+)["\']\s*:\s*\[[^\]]*["\']{re.escape(tool_name)}["\']''',
        re.DOTALL,
    )
    hints.extend(simple_pattern.findall(toolsets_text))
    return sorted(_unique(hints))


def _build_tool_descriptor(tool_path: Path, upstream_root: Path, toolsets_text: str) -> HermesToolDescriptor:
    relative_path = tool_path.relative_to(upstream_root).as_posix()
    text = _read_text(tool_path)
    registration_style = "none"
    registered = False
    tool_name = tool_path.stem
    requires_env: list[str] = []
    parse_error: str | None = None

    try:
        tree = ast.parse(text, filename=str(tool_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_register_call = isinstance(func, ast.Attribute) and func.attr == "register"
            if not is_register_call:
                continue
            registration_style = "registry.register"
            registered = True
            for keyword in node.keywords:
                if keyword.arg == "name":
                    value = _literal_str(keyword.value)
                    if value:
                        tool_name = value
                elif keyword.arg == "requires_env":
                    requires_env = _literal_str_list(keyword.value)
            break
    except SyntaxError as exc:
        parse_error = f"SyntaxError: {exc.msg}"

    return HermesToolDescriptor(
        id=tool_name,
        name=tool_name,
        path=relative_path,
        source="builtin",
        toolset_hints=_extract_toolset_hints(tool_name, toolsets_text),
        requires_env=requires_env,
        registration_style=registration_style,
        registered=registered,
        parse_error=parse_error,
    )


def _build_tool_descriptors(upstream_root: Path) -> list[HermesToolDescriptor]:
    toolsets_text = _read_text(upstream_root / "toolsets.py")
    descriptors: list[HermesToolDescriptor] = []
    for relative_path in _discover_paths(upstream_root, _TOOL_DISCOVERY_PATTERNS):
        tool_path = upstream_root / relative_path
        if tool_path.name == "__init__.py":
            continue
        descriptors.append(_build_tool_descriptor(tool_path, upstream_root, toolsets_text))
    return descriptors


def _build_memory_manager_descriptor(upstream_root: Path) -> HermesMemoryManagerDescriptor:
    manager_text = _read_text(upstream_root / "agent" / "memory_manager.py")
    provider_text = _read_text(upstream_root / "agent" / "memory_provider.py")
    public_api = [
        name
        for name, _ in _MEMORY_OPERATIONS
        if re.search(rf'^\s*def\s+{re.escape(name)}\b', manager_text, re.MULTILINE)
    ]
    helper_functions = [
        name
        for name in ("sanitize_context", "build_memory_context_block", "StreamingContextScrubber")
        if name in manager_text
    ]
    features: list[str] = []
    if "Only ONE external plugin provider is allowed" in manager_text:
        features.append("single-external-provider")
    if "build_memory_context_block" in manager_text:
        features.append("memory-context-fencing")
    if "queue_prefetch_all" in manager_text:
        features.append("background-prefetch")
    if "get_tool_schemas" in provider_text:
        features.append("provider-tools")
    if "get_config_schema" in provider_text:
        features.append("provider-config")
    return HermesMemoryManagerDescriptor(
        manager_path="agent/memory_manager.py",
        provider_base_path="agent/memory_provider.py",
        public_api=public_api,
        helper_functions=helper_functions,
        features=_unique(features),
        plugin_roots=[path for path in ("plugins/memory",) if (upstream_root / path).exists()],
    )


def _build_memory_operations(upstream_root: Path) -> list[HermesMemoryOperation]:
    manager_text = _read_text(upstream_root / "agent" / "memory_manager.py")
    operations: list[HermesMemoryOperation] = []
    for name, category in _MEMORY_OPERATIONS:
        pattern = re.compile(rf'^\s*def\s+{re.escape(name)}\b', re.MULTILINE)
        operations.append(
            HermesMemoryOperation(
                name=name,
                category=category,
                available=bool(pattern.search(manager_text)),
            )
        )
    return operations


def _extract_class_methods(text: str, class_name: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
    return []


def _extract_config_keys(text: str) -> list[str]:
    keys: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return keys
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        dict_keys = [_literal_str(key) for key in node.keys if key is not None]
        if not dict_keys:
            continue
        interesting = {"key", "description", "secret", "required", "default", "choices", "url", "env_var"}
        if interesting.intersection(dict_keys):
            for key in dict_keys:
                if key and key not in interesting:
                    keys.append(key)
    return _unique(keys)


def _build_memory_provider_descriptor(provider_path: Path, upstream_root: Path) -> HermesMemoryProviderDescriptor:
    relative_path = provider_path.relative_to(upstream_root).as_posix()
    text = _read_text(provider_path)
    parse_error: str | None = None
    hooks: list[str] = []
    loadable = False
    provider_name = provider_path.parent.name
    try:
        hooks = [name for name in _MEMORY_PROVIDER_HOOKS if re.search(rf'^\s*def\s+{re.escape(name)}\b', text, re.MULTILINE)]
        class_methods = _extract_class_methods(text, "MemoryProvider")
        if class_methods:
            hooks = [name for name in hooks if name not in class_methods]
        loadable = "class" in text and bool(hooks or "register" in text or "Provider" in text)
    except SyntaxError as exc:
        parse_error = f"SyntaxError: {exc.msg}"

    name_match = re.search(r'@property\s+\n\s*@abstractmethod\s+\n\s*def\s+name', text)
    if name_match:
        provider_name = "memory-provider-base"
    return HermesMemoryProviderDescriptor(
        id=provider_path.parent.name,
        name=provider_name,
        path=relative_path,
        source="plugin" if "plugins/memory/" in relative_path else "builtin",
        provider_kind="abstract-base" if provider_path.name == "memory_provider.py" else "plugin",
        loadable=loadable,
        hooks=hooks,
        config_fields=_extract_config_keys(text),
        parse_error=parse_error,
    )


def _build_memory_provider_descriptors(upstream_root: Path) -> list[HermesMemoryProviderDescriptor]:
    descriptors = [
        _build_memory_provider_descriptor(upstream_root / "agent" / "memory_provider.py", upstream_root)
    ]
    for provider_path in sorted((upstream_root / "plugins" / "memory").glob("*/__init__.py")) if (upstream_root / "plugins" / "memory").exists() else []:
        descriptors.append(_build_memory_provider_descriptor(provider_path, upstream_root))
    return descriptors


def _build_placeholder_snapshot(spec: _PlaceholderSpec, runtime_snapshot: HermesRuntimeSnapshot) -> HermesIntegrationSnapshot:
    upstream_root = Path(runtime_snapshot.upstream_root)
    surfaces = _surface_lookup(runtime_snapshot)
    available_surfaces = [
        surface_id
        for surface_id in spec.required_surfaces
        if surfaces.get(surface_id) is not None and surfaces[surface_id].available
    ]
    missing_surfaces = [surface_id for surface_id in spec.required_surfaces if surface_id not in available_surfaces]
    detected_entrypoints = _detect_entrypoints(upstream_root, spec.source_paths, spec.entrypoints)
    discovered_paths = _discover_paths(upstream_root, spec.discovery_patterns) if runtime_snapshot.checkout_present else []

    warnings: list[str] = []
    if missing_surfaces:
        warnings.append(f"Missing Hermes surfaces for {spec.surface}: {', '.join(missing_surfaces)}.")
    if not runtime_snapshot.import_ready:
        warnings.append("Hermes checkout is not import-ready; placeholder remains discovery-only.")
    if not detected_entrypoints and not missing_surfaces:
        warnings.append(f"Expected Hermes entrypoints for {spec.surface} were not detected in vendored sources.")
    warnings.extend(runtime_snapshot.warnings)

    return HermesIntegrationSnapshot(
        surface=spec.surface,
        integration_mode="discovery-only",
        status="placeholder" if not missing_surfaces else "blocked",
        placeholder=True,
        bridge_ready=False,
        upstream_available=not missing_surfaces,
        checkout_import_ready=runtime_snapshot.import_ready,
        worktree_state=runtime_snapshot.worktree_state,
        source_paths=list(spec.source_paths),
        required_surfaces=list(spec.required_surfaces),
        available_surfaces=available_surfaces,
        detected_entrypoints=detected_entrypoints,
        planned_operations=list(spec.planned_operations),
        discovered_count=len(discovered_paths),
        sample_paths=discovered_paths[:20],
        warnings=_unique(warnings),
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
        warnings = _unique(
            [
                f"Memory provider metadata issue for {provider.path}: {provider.parse_error}"
                for provider in providers
                if provider.parse_error
            ]
        )
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
        warnings = _unique(
            [
                f"Skill metadata issue for {skill.path}: {skill.parse_error}"
                for skill in skills
                if skill.parse_error
            ]
        )
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
        warnings = _unique(
            [
                f"Tool metadata issue for {tool.path}: {tool.parse_error}"
                for tool in tools
                if tool.parse_error
            ]
        )
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
