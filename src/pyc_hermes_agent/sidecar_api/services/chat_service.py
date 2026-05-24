"""Chat and agent loop service functions."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Dict, TypedDict
from uuid import uuid4

import json

from pyc_hermes_agent.contracts import (
    AgentLoopEvent,
    AgentLoopRequest,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResult,
    MetaAnalysisRequest,
    ToolCallResult,
)
from pyc_hermes_agent.hermes_engine import AgentLoop
from pyc_hermes_agent.llm_gateway import (
    execute_chat,
    LLMChatRequest,
    LLMMessage,
    resolve_opencode_like_config,
    stream_chat,
)
from pyc_hermes_agent.meta_harness import MetaFramework
from pyc_hermes_agent.meta_harness.evidence_chain import build_evidence_validation_pack
from pyc_hermes_agent.meta_harness.evidence_hints import summarize_formal_multi_source_evidence_chain
from pyc_hermes_agent.sidecar_api.error_domains import DOMAIN_AGENT, DOMAIN_LLM
from pyc_hermes_agent.sidecar_api.services._normalize import (
    normalize_agent_loop_request,
    normalize_chat_request,
)
from pyc_hermes_agent.sidecar_api.services.common import (
    _error,
    _repo_root,
    _serialize,
    log_event,
    make_error_response,
)


class _AgentLoopRunKwargs(TypedDict, total=False):
    max_iterations: int
    session_id: str | None
    activated_skills: list[str]
    planning_enabled: bool
    retry_budget: int
    analysis_mode: str
    working_memory: list[str]
    update_working_memory: bool


def _to_llm_messages(request: ChatCompletionRequest) -> list:
    return [
        LLMMessage(
            role=m.role,
            content=m.content,
            tool_call_id=m.tool_call_id,
            tool_calls=list(m.tool_calls),
        )
        for m in request.messages
    ]


def invoke_chat_completion(request: ChatCompletionRequest, root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    try:
        nr = normalize_chat_request(request)
        model_id = nr.model or resolve_opencode_like_config(base).default_model
        log_event("llm.chat.started", model=model_id)
        result = execute_chat(
            LLMChatRequest(
                model=nr.model,
                messages=_to_llm_messages(nr),
                tools=nr.tools,
                temperature=nr.temperature,
                max_tokens=nr.max_tokens,
                timeout_seconds=nr.timeout_seconds,
                retry_attempts=nr.retry_attempts,
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
    nr = normalize_chat_request(request)
    model_id = nr.model or resolve_opencode_like_config(base).default_model
    log_event("llm.chat.stream.started", model=model_id)
    try:
        for chunk in stream_chat(
            LLMChatRequest(
                model=nr.model,
                messages=_to_llm_messages(nr),
                tools=nr.tools,
                temperature=nr.temperature,
                max_tokens=nr.max_tokens,
                timeout_seconds=nr.timeout_seconds,
                retry_attempts=nr.retry_attempts,
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


def _maybe_json_mapping(text: object) -> dict[str, Any]:
    if not isinstance(text, str):
        return {}
    snippet = text.strip()
    if not snippet:
        return {}
    try:
        blob = json.loads(snippet)
    except Exception:
        return {}
    return blob if isinstance(blob, dict) else {}


def _gather_citations_nested(node: object, *, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 8:
        return []
    out: list[dict[str, Any]] = []
    if isinstance(node, list):
        for el in node:
            out.extend(_gather_citations_nested(el, depth=depth + 1))
        return out
    if not isinstance(node, Mapping):
        return []
    cites = node.get("citations")
    if isinstance(cites, list):
        for item in cites:
            if isinstance(item, Mapping):
                out.append(dict(item))
    for key in ("retrieval", "result"):
        child = node.get(key)
        out.extend(_gather_citations_nested(child, depth=depth + 1))
    return out


def _tool_citation_dicts(
    structured: Mapping[str, Any] | dict[str, Any],
    content: str,
) -> list[dict[str, Any]]:
    bodies: list[Mapping[str, Any]] = []
    if isinstance(structured, Mapping) and structured:
        bodies.append(structured)
    parsed = _maybe_json_mapping(content)
    if parsed:
        bodies.append(parsed)

    merged: list[dict[str, Any]] = []
    seen_fp: set[tuple[str, str, str]] = set()
    for body in bodies:
        for cite in _gather_citations_nested(body):
            fp = (
                str(cite.get("source_uri") or "").strip(),
                str(cite.get("document_id") or "").strip(),
                str(cite.get("chunk_id") or "").strip(),
            )
            if fp in seen_fp:
                continue
            seen_fp.add(fp)
            merged.append(cite)
    return merged


def _is_http_ref(ref: str) -> bool:
    r = ref.strip()
    return r.lower().startswith(("http://", "https://"))


def _cite_to_data_ref(cite: Mapping[str, Any]) -> str:
    uri = str(cite.get("source_uri") or "").strip()
    doc = str(cite.get("document_id") or "").strip()
    chk = str(cite.get("chunk_id") or "").strip()
    if uri:
        return uri
    if doc and chk:
        return f"pyc-hermes:mrag/{doc}/{chk}"
    if doc:
        return f"pyc-hermes:mrag/{doc}"
    return ""


def _classification_lane(tool_name: str, cite: Mapping[str, Any]) -> str | None:
    tn = (tool_name or "").strip()
    if tn == "formal_analysis":
        return None
    if tn == "knowledge_retrieve":
        return "kb"
    if tn == "web_search":
        return "web"

    uri = str(cite.get("source_uri") or "").strip()
    doc = str(cite.get("document_id") or "").strip()
    chk = str(cite.get("chunk_id") or "").strip()
    if doc or chk:
        return "kb"

    low_type = str(cite.get("source_type") or "").lower()
    if low_type and low_type not in {"", "unknown"}:
        return "kb"
    if uri.startswith(("http://", "https://")):
        return "web"

    # Path-like or chunk-only payloads default to KB context.
    return "kb"


def _formal_grounding_from_tool_results(
    tool_results: Sequence[Any] | None,
) -> tuple[list[str], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    web_citations: list[dict[str, Any]] = []
    kb_citations: list[dict[str, Any]] = []
    web_uri_rows: list[str] = []
    web_missing_uri = 0
    kb_missing_ref = 0

    for raw in tool_results or []:
        structured: Mapping[str, Any] | dict[str, Any]
        err: bool
        name: str
        content: str

        if isinstance(raw, ToolCallResult):
            name = raw.name
            err = raw.is_error
            structured = raw.structured_content or {}
            content = raw.content or ""
        elif isinstance(raw, Mapping):
            name = str(raw.get("name", "") or "")
            err = bool(raw.get("is_error"))
            sc = raw.get("structured_content")
            structured = sc if isinstance(sc, dict) else {}
            content = str(raw.get("content", "") or "")
        else:
            continue

        if err:
            continue

        for cite in _tool_citation_dicts(structured, content):
            lane = _classification_lane(name, cite)
            if lane is None:
                continue

            if lane == "web":
                web_citations.append(dict(cite))
                uri = str(cite.get("source_uri") or "").strip()
                if uri:
                    web_uri_rows.append(uri)
                else:
                    web_missing_uri += 1
            else:
                kb_citations.append(dict(cite))
                ref_s = _cite_to_data_ref(cite)
                if not ref_s:
                    kb_missing_ref += 1

    web_unique: list[str] = []
    seen_http: set[str] = set()
    for u in web_uri_rows:
        if u in seen_http:
            continue
        seen_http.add(u)
        web_unique.append(u)

    kb_unique: list[str] = []
    seen_kb: set[str] = set()
    for cite in kb_citations:
        ref_s = _cite_to_data_ref(cite)
        if not ref_s or ref_s in seen_kb:
            continue
        seen_kb.add(ref_s)
        kb_unique.append(ref_s)

    merged_refs: list[str] = []
    seen_all: set[str] = set()
    for candidate in [*web_unique, *kb_unique]:
        if candidate in seen_all:
            continue
        seen_all.add(candidate)
        merged_refs.append(candidate)

    merged_refs = merged_refs[:48]
    web_http_set = set(web_unique)
    overlaps: list[str] = []
    seen_overlap: set[str] = set()
    for cite in kb_citations:
        u = str(cite.get("source_uri") or "").strip()
        if _is_http_ref(u) and u in web_http_set and u not in seen_overlap:
            seen_overlap.add(u)
            overlaps.append(u)

    grounding_bundle = {
        "network_grounding": {
            "network_citations": web_citations,
            "citation_count": len(web_citations),
        },
        "local_kb_grounding": {
            "citations": kb_citations,
            "citation_count": len(kb_citations),
        },
    }

    web_stats = {
        "citation_entry_count": len(web_citations),
        "citations_missing_uri": web_missing_uri,
        "aggregated_uri_rows_before_dedupe": len(web_uri_rows),
        "unique_network_uris": len(web_unique),
    }

    doc_ids = {str(c.get("document_id") or "").strip() for c in kb_citations if str(c.get("document_id") or "").strip()}
    kb_stats = {
        "citation_entry_count": len(kb_citations),
        "distinct_documents": len(doc_ids),
        "citations_missing_ref": kb_missing_ref,
    }

    return merged_refs, grounding_bundle, web_stats, kb_stats, overlaps


def _build_analysis_card(
    problem_statement: str,
    *,
    tool_results: Sequence[Any] | None = None,
) -> Dict[str, Any] | None:
    """Run MetaFramework.execute() with multi-source grounding (`web_search` + MRAG-shaped citations)."""

    grounding_refs, grounding_bundle, web_stats, kb_stats, overlaps = _formal_grounding_from_tool_results(tool_results)

    http_only = [r for r in grounding_refs if _is_http_ref(r)]

    try:
        fw = MetaFramework()

        merged_data: dict[str, Any] = {
            **grounding_bundle,
            "network_grounding_stats": web_stats,
            "local_kb_grounding_stats": kb_stats,
        }

        req = MetaAnalysisRequest(
            problem_statement=problem_statement,
            data_refs=grounding_refs,
            data=merged_data,
        )

        result = fw.execute(req)
        ms = summarize_formal_multi_source_evidence_chain(
            http_refs=http_only,
            web_stats=web_stats,
            kb_stats=kb_stats,
            overlapping_http_across_kb_and_web=overlaps,
        )

        hints_list = list(ms.get("hints") or [])
        if int(web_stats.get("citations_missing_uri") or 0) > 0:
            hints_list.append("network_citations_missing_source_uri")
        if int(kb_stats.get("citations_missing_ref") or 0) > 0:
            hints_list.append("kb_citations_missing_document_or_uri_ref")

        web_sub = ms.get("web")
        if not isinstance(web_sub, dict):
            web_sub = {}

        evidence_chain: dict[str, Any] = dict(ms)
        evidence_chain["hints"] = hints_list
        evidence_chain["distinct_host_count"] = int(web_sub.get("distinct_host_count") or 0)
        evidence_chain["hosts"] = list(web_sub.get("hosts") or [])
        evidence_chain["stats"] = {"web": web_stats, "kb": kb_stats}
        evidence_chain["validation"] = build_evidence_validation_pack(
            problem_statement=problem_statement,
            web_citations=list(grounding_bundle["network_grounding"].get("network_citations") or []),
            kb_citations=list(grounding_bundle["local_kb_grounding"].get("citations") or []),
            web_stats=web_stats,
            kb_stats=kb_stats,
            overlapping_http_across_kb_and_web=overlaps,
            meta_result=result,
            http_refs_summary=tuple(http_only),
        )

        payload = {
            "method": result.selected_method,
            "evidence_grade": result.evidence_grade,
            "sr_grade": result.sr_grade,
            "risks": list(result.risks),
            "assumptions": list(result.assumptions),
            "rationale": result.method_rationale,
            "degraded": result.degraded,
            "network_refs": http_only,
            "formal_grounding_refs": grounding_refs,
            "network_citations": grounding_bundle["network_grounding"].get("network_citations", []),
            "local_kb_citations": grounding_bundle["local_kb_grounding"].get("citations", []),
            "evidence_chain": evidence_chain,
        }

        return payload

    except Exception as exc:
        log_event("analysis_card.failed", error=str(exc))

        return None


def _build_run_kwargs(nr: AgentLoopRequest) -> _AgentLoopRunKwargs:
    run_kwargs: _AgentLoopRunKwargs = {
        "max_iterations": nr.max_iterations,
        "session_id": nr.session_id,
    }
    if nr.activated_skills:
        run_kwargs["activated_skills"] = nr.activated_skills
    if nr.planning_enabled is False:
        run_kwargs["planning_enabled"] = False
    if nr.retry_budget != 1:
        run_kwargs["retry_budget"] = nr.retry_budget
    if nr.analysis_mode != "casual":
        run_kwargs["analysis_mode"] = nr.analysis_mode
    if nr.update_working_memory:
        run_kwargs["update_working_memory"] = True
        run_kwargs["working_memory"] = list(nr.working_memory)
    return run_kwargs


def _agent_chat_request(nr: AgentLoopRequest) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model=nr.model,
        messages=nr.messages,
        tools=nr.tools,
        temperature=nr.temperature,
        max_tokens=nr.max_tokens,
        timeout_seconds=nr.timeout_seconds,
        retry_attempts=nr.retry_attempts,
    )


def _extract_last_user_message(nr: AgentLoopRequest) -> str:
    """Extract the last user message content for formal analysis."""
    for msg in reversed(nr.messages):
        if msg.role == "user":
            return msg.content
    return ""


def run_agent_loop(request: AgentLoopRequest, root: Path | None = None) -> Dict[str, Any]:
    base = root or _repo_root()
    try:
        nr = normalize_agent_loop_request(request)
        model_id = nr.model or resolve_opencode_like_config(base).default_model
        log_event("agent.loop.started", model=model_id, max_iterations=nr.max_iterations)
        result = AgentLoop(root=base).run(_agent_chat_request(nr), **_build_run_kwargs(nr))
        log_event(
            "agent.loop.finished",
            model=result.model,
            provider_id=result.provider_id,
            finish_reason=result.finish_reason or "unknown",
            iterations=result.iterations,
        )
        serialized = _serialize(result)
        if nr.analysis_mode == "formal":
            problem = _extract_last_user_message(nr)

            card = _build_analysis_card(problem, tool_results=result.tool_results)

            if card:
                serialized["analysis_card"] = card
        return serialized
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
    nr = normalize_agent_loop_request(request)
    model_id = nr.model or resolve_opencode_like_config(base).default_model
    log_event("agent.loop.stream.started", model=model_id, max_iterations=nr.max_iterations)
    run_kwargs = _build_run_kwargs(nr)

    try:
        for event in AgentLoop(root=base).stream(_agent_chat_request(nr), **run_kwargs):
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
                if nr.analysis_mode == "formal":
                    problem = _extract_last_user_message(nr)

                    serialized_tool_blob: list[Any] = []

                    blob = payload.get("payload")

                    if isinstance(blob, dict):
                        res_blob = blob.get("result")

                        if isinstance(res_blob, dict):
                            tr = res_blob.get("tool_results")

                            if isinstance(tr, list):
                                serialized_tool_blob = tr

                    card = _build_analysis_card(problem, tool_results=serialized_tool_blob)

                    if card:
                        payload["analysis_card"] = card
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
            session_id=nr.session_id,
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
