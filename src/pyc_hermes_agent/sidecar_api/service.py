"""Minimum sidecar service API."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from uuid import uuid4
from collections.abc import Iterator
from typing import Any, Dict, List

from pyc_hermes_agent import __version__
from pyc_hermes_agent.asset_manager import AssetManager
from pyc_hermes_agent.artifact_engine import ArtifactEngine, ArtifactRecord
from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import AgentLoopEvent, AgentLoopRequest, ChatCompletionChunk, ChatCompletionRequest, ChatCompletionResult, ChatMessage, ErrorEnvelope, EventEnvelope, MetaAnalysisRequest, TaskResult, ToolCall, ToolDefinition
from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.hermes_engine import AgentLoop, HermesFacade
from pyc_hermes_agent.llm_gateway import (
    discover_rule_files,
    execute_chat,
    LLMChatRequest,
    stream_chat,
    LLMMessage,
    load_skill_metadata,
    resolve_opencode_like_config,
)
from pyc_hermes_agent.meta_harness import MetaFramework
from pyc_hermes_agent.meta_harness.benchmark import run_value_proof_benchmark
from pyc_hermes_agent.mrag_core import MRAGService
from pyc_hermes_agent.sidecar_api.error_domains import (
    DOMAIN_AGENT,
    DOMAIN_INTERNAL,
    DOMAIN_LLM,
    DOMAIN_META_HARNESS,
)
from pyc_hermes_agent.sidecar_api.logging import log_event


_MRAG_SERVICES: dict[str, MRAGService] = {}
SIDECAR_API_VERSION = "0.2"

_SKILLS_RUNTIME_POLICY: Dict[str, str] = {
    "activation_mode": "explicit_only",
    "script_execution": "disabled",
    "agent_loop_field": "activated_skills",
}


def _artifact_record_payload(record: ArtifactRecord) -> Dict[str, Any]:
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _normalize_chat_request(request: ChatCompletionRequest) -> ChatCompletionRequest:
    messages = []
    for message in request.messages:
        if isinstance(message, ChatMessage):
            messages.append(message)
            continue
        if isinstance(message, dict):
            tool_calls = []
            for call in message.get("tool_calls", []):
                if not isinstance(call, dict):
                    raise TypeError(f"Unsupported tool call payload: {type(call)!r}")
                if "function" in call and isinstance(call["function"], dict):
                    function_payload = call["function"]
                    tool_calls.append(
                        ToolCall(
                            id=str(call.get("id", "")),
                            type=str(call.get("type", "function")),
                            name=str(function_payload.get("name", "")),
                            arguments=str(function_payload.get("arguments", "{}")),
                        )
                    )
                    continue
                tool_calls.append(ToolCall(**call))
            messages.append(
                ChatMessage(
                    role=str(message.get("role", "user")),
                    content=str(message.get("content", "")),
                    tool_call_id=str(message["tool_call_id"]) if message.get("tool_call_id") is not None else None,
                    tool_calls=tool_calls,
                )
            )
            continue
        raise TypeError(f"Unsupported chat message payload: {type(message)!r}")

    tools = []
    for tool in request.tools:
        if isinstance(tool, ToolDefinition):
            tools.append(tool)
            continue
        if isinstance(tool, dict):
            if "function" in tool and isinstance(tool["function"], dict):
                function_payload = tool["function"]
                tools.append(
                    ToolDefinition(
                        type=str(tool.get("type", "function")),
                        name=str(function_payload.get("name", "")),
                        description=str(function_payload.get("description", "")),
                        parameters=function_payload.get("parameters", {"type": "object", "properties": {}}),
                        strict=bool(function_payload.get("strict", False)),
                    )
                )
                continue
            tools.append(ToolDefinition(**tool))
            continue
        raise TypeError(f"Unsupported tool definition payload: {type(tool)!r}")

    return ChatCompletionRequest(
        model=request.model,
        messages=messages,
        tools=tools,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        timeout_seconds=request.timeout_seconds,
        retry_attempts=request.retry_attempts,
    )


def _normalize_agent_loop_request(request: AgentLoopRequest) -> AgentLoopRequest:
    normalized_chat = _normalize_chat_request(
        ChatCompletionRequest(
            model=request.model,
            messages=request.messages,
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout_seconds=request.timeout_seconds,
            retry_attempts=request.retry_attempts,
        )
    )
    return AgentLoopRequest(
        session_id=request.session_id,
        model=normalized_chat.model,
        messages=normalized_chat.messages,
        tools=normalized_chat.tools,
        activated_skills=list(request.activated_skills),
        planning_enabled=request.planning_enabled,
        retry_budget=request.retry_budget,
        temperature=normalized_chat.temperature,
        max_tokens=normalized_chat.max_tokens,
        timeout_seconds=normalized_chat.timeout_seconds,
        retry_attempts=normalized_chat.retry_attempts,
        max_iterations=request.max_iterations,
    )


def _get_mrag_service(root: Path | None = None) -> MRAGService:
    runtime_paths = ensure_runtime_directories(resolve_runtime_paths(resolve_runtime_directories_root(root)))
    storage_root = runtime_paths.mrag_dir
    cache_key = str(storage_root)
    service = _MRAG_SERVICES.get(cache_key)
    if service is None:
        service = MRAGService(storage_root=storage_root)
        _MRAG_SERVICES[cache_key] = service
    return service


def resolve_runtime_directories_root(root: Path | None = None) -> Path | None:
    if root is None:
        return None
    return root.resolve()


def _get_hermes_facade(root: Path | None = None) -> HermesFacade:
    base = root or _repo_root()
    # Hermes discovery and health reads should reflect current upstream state,
    # not a process-lifetime snapshot captured by an earlier request.
    return HermesFacade(root=base)


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


def get_health(root: Path | None = None) -> dict:
    bridge_health = get_hermes_bridge_health(root)
    ready_state = "unavailable"
    if bridge_health["bridge_ready"]:
        ready_state = "ready"
    elif bridge_health["checkout_present"] and bridge_health["import_ready"]:
        ready_state = "degraded"
    status_label = ready_state
    if ready_state == "ready" and bridge_health["warnings"]:
        status_label = "ready-with-warnings"
    return {
        "healthy": True,
        "degraded": ready_state != "ready",
        "status_label": status_label,
        "version": __version__,
        "sidecar_api_version": SIDECAR_API_VERSION,
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
    base = root or _repo_root()
    resolved = resolve_opencode_like_config(base)
    return {
        "config_path": str(resolved.config_path) if resolved.config_path else None,
        "default_model": resolved.default_model,
        "small_model": resolved.small_model,
        "free_first": resolved.free_first,
    }


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


def list_providers(root: Path | None = None) -> List[Dict[str, Any]]:
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


def list_models(root: Path | None = None) -> List[Dict[str, Any]]:
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


def list_rules(root: Path | None = None) -> List[Dict[str, Any]]:
    base = root or _repo_root()
    return [{"path": str(path), "name": path.name} for path in discover_rule_files(base)]


def list_skills(root: Path | None = None) -> List[Dict[str, Any]]:
    base = root or _repo_root()
    items: List[Dict[str, Any]] = []
    for skill in load_skill_metadata(base):
        mtime_ns = skill.path.stat().st_mtime_ns
        items.append(
            {
                "name": skill.name,
                "description": skill.description,
                "path": str(skill.path),
                "license": skill.license,
                "compatibility": skill.compatibility,
                "metadata": skill.metadata,
                "runtime": {
                    "policy": dict(_SKILLS_RUNTIME_POLICY),
                    "source": {
                        "kind": "SKILL.md",
                        "path": str(skill.path),
                        "mtime_ns": mtime_ns,
                    },
                },
            }
        )
    return items


def list_asset_inventory(root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    manager = AssetManager(root=base)
    return {"items": manager.list_installed_assets()}


def list_sidecar_artifacts(root: Path | None = None, *, task_id: str | None = None) -> Dict[str, Any]:
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


def invoke_formal_analysis(request: MetaAnalysisRequest) -> Dict[str, Any]:
    framework = MetaFramework()
    task_id = request.problem_statement[:32] or "formal-analysis"
    started = _event("sidecar", "task.started", task_id, {"mode": "formal-analysis"})
    try:
        result = framework.execute(request)
        finished = _event(
            "sidecar",
            "task.finished",
            task_id,
            {
                "selected_method": result.selected_method,
                "degraded": result.degraded,
                "evidence_grade": result.evidence_grade,
            },
        )
        task_result = TaskResult(
            task_id=task_id,
            status="degraded" if result.degraded else "success",
            summary=result.method_rationale,
            outputs=[{"meta_analysis": _serialize(result)}],
            warnings=result.risks,
            trace_ref=result.selected_method or None,
        )
        return {
            "events": [started, finished],
            "result": _serialize(task_result),
            "analysis": _serialize(result),
        }
    except Exception as exc:
        failure = _event("sidecar", "task.failed", task_id, {"mode": "formal-analysis"})
        response = make_error_response(
            "FORMAL_ANALYSIS_FAILED",
            "internal",
            str(exc),
            domain=DOMAIN_META_HARNESS,
            degraded=False,
        )
        response["events"] = [started, failure]
        return response


def get_meta_harness_dependency_snapshot() -> Dict[str, Any]:
    return MetaFramework().dependency_snapshot()


def get_meta_harness_benchmark_smoke() -> Dict[str, Any]:
    return MetaFramework().run_benchmark_smoke()


def get_meta_harness_value_proof_benchmark() -> Dict[str, Any]:
    return run_value_proof_benchmark()


def invoke_chat_completion(request: ChatCompletionRequest, root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    try:
        normalized_request = _normalize_chat_request(request)
        model_id = normalized_request.model or resolve_opencode_like_config(base).default_model
        log_event("llm.chat.started", model=model_id)
        result = execute_chat(
            LLMChatRequest(
                model=normalized_request.model,
                messages=[
                    LLMMessage(
                        role=message.role,
                        content=message.content,
                        tool_call_id=message.tool_call_id,
                        tool_calls=list(message.tool_calls),
                    )
                    for message in normalized_request.messages
                ],
                tools=normalized_request.tools,
                temperature=normalized_request.temperature,
                max_tokens=normalized_request.max_tokens,
                timeout_seconds=normalized_request.timeout_seconds,
                retry_attempts=normalized_request.retry_attempts,
            ),
            base,
        )
        log_event(
            "llm.chat.finished",
            model=result.model,
            provider_id=result.provider_id,
            finish_reason=result.finish_reason or "unknown",
        )
        return _serialize(
            ChatCompletionResult(
                model=result.model,
                provider_id=result.provider_id,
                content=result.content,
                tool_calls=result.tool_calls,
                finish_reason=result.finish_reason,
                usage=result.usage,
                raw_response=result.raw_response,
            )
        )
    except Exception as exc:
        log_event("llm.chat.failed", error=str(exc))
        return make_error_response(
            "LLM_CHAT_FAILED",
            "provider",
            str(exc),
            domain=DOMAIN_LLM,
            retryable=True,
            degraded=False,
        )


def stream_chat_completion(request: ChatCompletionRequest, root: Path | None = None) -> Iterator[Dict[str, Any]]:
    base = root or _repo_root()
    normalized_request = _normalize_chat_request(request)
    model_id = normalized_request.model or resolve_opencode_like_config(base).default_model
    log_event("llm.chat.stream.started", model=model_id)
    try:
        for chunk in stream_chat(
            LLMChatRequest(
                model=normalized_request.model,
                messages=[
                    LLMMessage(
                        role=message.role,
                        content=message.content,
                        tool_call_id=message.tool_call_id,
                        tool_calls=list(message.tool_calls),
                    )
                    for message in normalized_request.messages
                ],
                tools=normalized_request.tools,
                temperature=normalized_request.temperature,
                max_tokens=normalized_request.max_tokens,
                timeout_seconds=normalized_request.timeout_seconds,
                retry_attempts=normalized_request.retry_attempts,
            ),
            base,
        ):
            payload = _serialize(
                ChatCompletionChunk(
                    event=chunk.event,
                    model=chunk.model,
                    provider_id=chunk.provider_id,
                    delta=chunk.delta,
                    content=chunk.content,
                    tool_calls=chunk.tool_calls,
                    finish_reason=chunk.finish_reason,
                    usage=chunk.usage,
                    error=chunk.error,
                    raw_response=chunk.raw_response,
                )
            )
            if chunk.event == "done":
                log_event(
                    "llm.chat.stream.finished",
                    model=chunk.model,
                    provider_id=chunk.provider_id,
                    finish_reason=chunk.finish_reason or "unknown",
                )
            yield payload
    except Exception as exc:
        log_event("llm.chat.stream.failed", error=str(exc))
        yield _serialize(
            ChatCompletionChunk(
                event="error",
                model=model_id,
                provider_id="",
                error=_error(
                    "LLM_CHAT_STREAM_FAILED",
                    "provider",
                    str(exc),
                    domain=DOMAIN_LLM,
                    retryable=True,
                    degraded=False,
                ),
            )
        )


def run_agent_loop(request: AgentLoopRequest, root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    try:
        normalized_request = _normalize_agent_loop_request(request)
        model_id = normalized_request.model or resolve_opencode_like_config(base).default_model
        log_event("agent.loop.started", model=model_id, max_iterations=normalized_request.max_iterations)
        run_kwargs = {
            "max_iterations": normalized_request.max_iterations,
            "session_id": normalized_request.session_id,
        }
        if normalized_request.activated_skills:
            run_kwargs["activated_skills"] = normalized_request.activated_skills
        if normalized_request.planning_enabled is False:
            run_kwargs["planning_enabled"] = False
        if normalized_request.retry_budget != 1:
            run_kwargs["retry_budget"] = normalized_request.retry_budget

        result = AgentLoop(root=base).run(
            ChatCompletionRequest(
                model=normalized_request.model,
                messages=normalized_request.messages,
                tools=normalized_request.tools,
                temperature=normalized_request.temperature,
                max_tokens=normalized_request.max_tokens,
                timeout_seconds=normalized_request.timeout_seconds,
                retry_attempts=normalized_request.retry_attempts,
            ),
            **run_kwargs,
        )
        log_event(
            "agent.loop.finished",
            model=result.model,
            provider_id=result.provider_id,
            finish_reason=result.finish_reason or "unknown",
            iterations=result.iterations,
        )
        return _serialize(result)
    except Exception as exc:
        log_event("agent.loop.failed", error=str(exc))
        return make_error_response(
            "AGENT_LOOP_FAILED",
            "runtime",
            str(exc),
            domain=DOMAIN_AGENT,
            retryable=False,
            degraded=False,
        )


def stream_agent_loop(request: AgentLoopRequest, root: Path | None = None) -> Iterator[Dict[str, Any]]:
    base = root or _repo_root()
    normalized_request = _normalize_agent_loop_request(request)
    model_id = normalized_request.model or resolve_opencode_like_config(base).default_model
    log_event("agent.loop.stream.started", model=model_id, max_iterations=normalized_request.max_iterations)
    run_kwargs = {
        "max_iterations": normalized_request.max_iterations,
        "session_id": normalized_request.session_id,
    }
    if normalized_request.activated_skills:
        run_kwargs["activated_skills"] = normalized_request.activated_skills
    if normalized_request.planning_enabled is False:
        run_kwargs["planning_enabled"] = False
    if normalized_request.retry_budget != 1:
        run_kwargs["retry_budget"] = normalized_request.retry_budget

    try:
        for event in AgentLoop(root=base).stream(
            ChatCompletionRequest(
                model=normalized_request.model,
                messages=normalized_request.messages,
                tools=normalized_request.tools,
                temperature=normalized_request.temperature,
                max_tokens=normalized_request.max_tokens,
                timeout_seconds=normalized_request.timeout_seconds,
                retry_attempts=normalized_request.retry_attempts,
            ),
            **run_kwargs,
        ):
            payload = _serialize(event)
            if event.event == "done":
                log_event(
                    "agent.loop.stream.finished",
                    model=event.model,
                    provider_id=event.provider_id,
                    finish_reason=event.finish_reason or "unknown",
                    iterations=event.iteration,
                    trace_id=event.trace_id,
                    sequence=event.sequence,
                )
            elif event.event == "error":
                log_event(
                    "agent.loop.stream.failed",
                    error=event.error.get("message", "unknown"),
                    trace_id=event.trace_id,
                    sequence=event.sequence,
                )
            yield payload
    except Exception as exc:
        fallback_event = AgentLoopEvent(
            trace_id=str(uuid4()),
            sequence=1,
            event="error",
            is_terminal=True,
            session_id=normalized_request.session_id,
            model=model_id,
            error=_error(
                "AGENT_LOOP_STREAM_FAILED",
                "runtime",
                str(exc),
                domain=DOMAIN_AGENT,
                retryable=False,
                degraded=False,
            ),
        )
        log_event(
            "agent.loop.stream.failed",
            error=str(exc),
            trace_id=fallback_event.trace_id,
            sequence=fallback_event.sequence,
        )
        yield _serialize(fallback_event)


def list_knowledge_bases(root: Path | None = None) -> List[Dict[str, Any]]:
    return _get_mrag_service(root).list_knowledge_bases()


def create_knowledge_base(name: str, root: Path | None = None) -> Dict[str, Any]:
    kb = _get_mrag_service(root).create_knowledge_base(name)
    return {
        "knowledge_base_id": kb.knowledge_base_id,
        "name": kb.name,
        "documents": 0,
        "chunks": 0,
    }


def ingest_text_document(
    knowledge_base_id: str,
    text: str,
    *,
    title: str = "",
    source_uri: str = "",
    source_type: str = "text",
    root: Path | None = None,
) -> Dict[str, Any]:
    document = _get_mrag_service(root).ingest_text(
        knowledge_base_id,
        text,
        title=title,
        source_uri=source_uri,
        source_type=source_type,
    )
    return _serialize(document)


def ingest_file_document(knowledge_base_id: str, path: Path | str, *, root: Path | None = None) -> Dict[str, Any]:
    document = _get_mrag_service(root).ingest_file(knowledge_base_id, Path(path).expanduser())
    return _serialize(document)


def ingest_url_document(
    knowledge_base_id: str,
    url: str,
    text: str,
    *,
    title: str = "",
    root: Path | None = None,
) -> Dict[str, Any]:
    document = _get_mrag_service(root).ingest_url_text(knowledge_base_id, url, text, title=title)
    return _serialize(document)


def search_knowledge_base(knowledge_base_id: str, request: RetrievalRequest, root: Path | None = None) -> Dict[str, Any]:
    result = _get_mrag_service(root).search(knowledge_base_id, request)
    return _serialize(result)


def rebuild_mrag_chunk_index(knowledge_base_id: str, root: Path | None = None) -> Dict[str, Any]:
    count = _get_mrag_service(root).rebuild_chunk_index(knowledge_base_id)
    return {"knowledge_base_id": knowledge_base_id, "chunk_count": count, "status": "rebuilt"}
