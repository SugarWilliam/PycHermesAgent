"""Bridge functions that merge runtime probe results into integration snapshots."""

from __future__ import annotations

from dataclasses import replace

from pyc_hermes_agent.contracts import (
    HermesIntegrationSnapshot,
    HermesMemoryOperation,
    HermesMemoryProviderDescriptor,
    HermesSessionOperation,
    HermesSkillDescriptor,
    HermesToolDescriptor,
    HermesToolOperation,
)

from .constants import _coerce_runtime_int
from .discovery import _unique


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
