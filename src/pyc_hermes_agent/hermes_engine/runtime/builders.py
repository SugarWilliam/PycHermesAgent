"""Builder functions for session, tool, and memory descriptors and operations."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from pyc_hermes_agent.contracts import (
    HermesMemoryManagerDescriptor,
    HermesMemoryOperation,
    HermesMemoryProviderDescriptor,
    HermesSessionOperation,
    HermesSessionStoreDescriptor,
    HermesToolDescriptor,
    HermesToolOperation,
    HermesToolRegistryDescriptor,
)

from .constants import (
    _MEMORY_OPERATIONS,
    _MEMORY_PROVIDER_HOOKS,
    _SESSION_OPERATIONS,
    _TOOL_DISCOVERY_PATTERNS,
    _TOOL_OPERATIONS,
)
from .discovery import (
    _discover_paths,
    _extract_class_methods,
    _extract_config_keys,
    _literal_str,
    _literal_str_list,
    _read_text,
    _search_value,
    _unique,
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
