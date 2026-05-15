"""Small sidecar client helpers.

Product consumers should treat the top-level ``get_health()['status_label']`` as
the first readiness signal. Nested ``hermes`` fields are diagnostic detail only.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pyc_hermes_agent.contracts import AgentLoopRequest, ChatCompletionRequest, MetaAnalysisRequest, RetrievalRequest
from pyc_hermes_agent.sidecar_api.service import (
    create_knowledge_base,
    get_config_snapshot,
    get_health,
    get_hermes_bridge_health,
    get_hermes_capability_snapshot,
    get_hermes_memory_snapshot,
    get_hermes_sessions_snapshot,
    get_hermes_skills_snapshot,
    get_hermes_tools_snapshot,
    ingest_text_document,
    invoke_chat_completion,
    invoke_formal_analysis,
    list_knowledge_bases,
    list_models,
    list_providers,
    list_rules,
    list_skills,
    run_agent_loop,
    search_knowledge_base,
    stream_agent_loop,
    stream_chat_completion,
)


HealthFetcher = Callable[[Path | None], Mapping[str, Any]]


def _make_http_health_fetcher(base_url: str, timeout: float) -> HealthFetcher:
    normalized_base_url = base_url.rstrip("/")

    def fetch(_root: Path | None) -> Mapping[str, Any]:
        return _http_get_json(normalized_base_url, "/health", timeout)

    return fetch


def _serialize_payload(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return value


def _http_get_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    try:
        with urlopen(f"{base_url}{path}", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return _read_http_error_json(exc)


def _http_post_json(base_url: str, path: str, payload: Mapping[str, Any], timeout: float) -> dict[str, Any]:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(dict(payload)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return _read_http_error_json(exc)


def _http_post_stream(base_url: str, path: str, payload: Mapping[str, Any], timeout: float) -> Iterator[dict[str, Any]]:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(dict(payload)).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            yield from _iter_sse_json_events(response)
    except HTTPError as exc:
        yield _read_http_error_json(exc)


def _iter_sse_json_events(response: Any) -> Iterator[dict[str, Any]]:
    data_lines: list[str] = []
    while True:
        raw_line = response.readline()
        if not raw_line:
            if data_lines:
                yield json.loads("\n".join(data_lines))
            break
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_lines:
                yield json.loads("\n".join(data_lines))
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())


def _read_http_error_json(error: HTTPError) -> dict[str, Any]:
    body = error.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive boundary
        raise error from exc
    if not isinstance(parsed, dict):  # pragma: no cover - defensive boundary
        raise error
    return parsed


def _resolve_status_label(health: Mapping[str, Any]) -> str:
    status_label = health.get("status_label")
    if isinstance(status_label, str) and status_label:
        return status_label
    if health.get("degraded") is True:
        return "degraded"
    return "unavailable"


@dataclass(frozen=True)
class SidecarHealthStatus:
    """Top-level sidecar health view for product consumers."""

    status_label: str
    degraded: bool
    payload: dict[str, Any]


class SidecarClient:
    """Small wrapper that anchors health reads to the top-level status label."""

    def __init__(
        self,
        *,
        root: Path | None = None,
        health_fetcher: HealthFetcher = get_health,
        base_url: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._root = root
        self._base_url = base_url.rstrip("/") if base_url is not None else None
        self._timeout = timeout
        if base_url is not None:
            if health_fetcher is not get_health:
                raise ValueError("base_url and health_fetcher are mutually exclusive")
            self._health_fetcher = _make_http_health_fetcher(base_url, timeout)
        else:
            self._health_fetcher = health_fetcher

    def get_health(self) -> dict[str, Any]:
        return dict(self._health_fetcher(self._root))

    def get_config_snapshot(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/config")
        return get_config_snapshot(self._root)

    def get_hermes_bridge_health(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/hermes/bridge-health")
        return get_hermes_bridge_health(self._root)

    def get_hermes_capability_snapshot(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/hermes/capability")
        return get_hermes_capability_snapshot(self._root)

    def get_hermes_sessions_snapshot(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/hermes/sessions")
        return get_hermes_sessions_snapshot(self._root)

    def get_hermes_memory_snapshot(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/hermes/memory")
        return get_hermes_memory_snapshot(self._root)

    def get_hermes_skills_snapshot(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/hermes/skills")
        return get_hermes_skills_snapshot(self._root)

    def get_hermes_tools_snapshot(self) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_get("/hermes/tools")
        return get_hermes_tools_snapshot(self._root)

    def list_providers(self) -> list[dict[str, Any]]:
        if self._base_url is not None:
            return self._http_get_items("/providers")
        return list_providers(self._root)

    def list_models(self) -> list[dict[str, Any]]:
        if self._base_url is not None:
            return self._http_get_items("/models")
        return list_models(self._root)

    def list_rules(self) -> list[dict[str, Any]]:
        if self._base_url is not None:
            return self._http_get_items("/rules")
        return list_rules(self._root)

    def list_skills(self) -> list[dict[str, Any]]:
        if self._base_url is not None:
            return self._http_get_items("/skills")
        return list_skills(self._root)

    def invoke_formal_analysis(self, request: MetaAnalysisRequest | Mapping[str, Any]) -> dict[str, Any]:
        serialized_request = _serialize_payload(request)
        if not isinstance(serialized_request, dict):
            raise TypeError("Formal analysis request must be a mapping or dataclass.")
        if self._base_url is not None:
            return self._http_post("/formal-analysis", serialized_request)
        return invoke_formal_analysis(MetaAnalysisRequest(**serialized_request))

    def invoke_chat_completion(self, request: ChatCompletionRequest | Mapping[str, Any]) -> dict[str, Any]:
        serialized_request = _serialize_payload(request)
        if not isinstance(serialized_request, dict):
            raise TypeError("Chat completion request must be a mapping or dataclass.")
        if self._base_url is not None:
            return self._http_post("/llm/chat", serialized_request)
        return invoke_chat_completion(ChatCompletionRequest(**serialized_request), self._root)

    def stream_chat_completion(self, request: ChatCompletionRequest | Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        serialized_request = _serialize_payload(request)
        if not isinstance(serialized_request, dict):
            raise TypeError("Chat completion request must be a mapping or dataclass.")
        if self._base_url is not None:
            yield from _http_post_stream(self._base_url, "/llm/chat/stream", serialized_request, self._timeout)
            return
        yield from stream_chat_completion(ChatCompletionRequest(**serialized_request), self._root)

    def run_agent_loop(self, request: AgentLoopRequest | Mapping[str, Any]) -> dict[str, Any]:
        serialized_request = _serialize_payload(request)
        if not isinstance(serialized_request, dict):
            raise TypeError("Agent loop request must be a mapping or dataclass.")
        if self._base_url is not None:
            return self._http_post("/agent/run", serialized_request)
        return run_agent_loop(AgentLoopRequest(**serialized_request), self._root)

    def stream_agent_loop(self, request: AgentLoopRequest | Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        serialized_request = _serialize_payload(request)
        if not isinstance(serialized_request, dict):
            raise TypeError("Agent loop request must be a mapping or dataclass.")
        if self._base_url is not None:
            yield from _http_post_stream(self._base_url, "/agent/run/stream", serialized_request, self._timeout)
            return
        yield from stream_agent_loop(AgentLoopRequest(**serialized_request), self._root)

    def list_knowledge_bases(self) -> list[dict[str, Any]]:
        if self._base_url is not None:
            return self._http_get_items("/knowledge-bases")
        return list_knowledge_bases(self._root)

    def create_knowledge_base(self, name: str) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_post("/knowledge-bases", {"name": name})
        return create_knowledge_base(name, self._root)

    def ingest_text_document(
        self,
        knowledge_base_id: str,
        text: str,
        *,
        title: str = "",
        source_uri: str = "",
        source_type: str = "text",
    ) -> dict[str, Any]:
        if self._base_url is not None:
            return self._http_post(
                f"/knowledge-bases/{quote(knowledge_base_id, safe='')}/documents/text",
                {
                    "text": text,
                    "title": title,
                    "source_uri": source_uri,
                    "source_type": source_type,
                },
            )
        return ingest_text_document(
            knowledge_base_id,
            text,
            title=title,
            source_uri=source_uri,
            source_type=source_type,
            root=self._root,
        )

    def search_knowledge_base(self, knowledge_base_id: str, request: RetrievalRequest | Mapping[str, Any]) -> dict[str, Any]:
        serialized_request = _serialize_payload(request)
        if not isinstance(serialized_request, dict):
            raise TypeError("Retrieval request must be a mapping or dataclass.")
        if self._base_url is not None:
            return self._http_post(
                f"/knowledge-bases/{quote(knowledge_base_id, safe='')}/search",
                serialized_request,
            )
        return search_knowledge_base(knowledge_base_id, RetrievalRequest(**serialized_request), self._root)

    def get_health_status(self) -> SidecarHealthStatus:
        health = self.get_health()
        return SidecarHealthStatus(
            # Only honor the top-level label. If it is absent, collapse to a
            # minimal degraded or unavailable fallback without re-deriving Hermes state.
            status_label=_resolve_status_label(health),
            degraded=bool(health.get("degraded")),
            payload=health,
        )

    def _http_get(self, path: str) -> dict[str, Any]:
        if self._base_url is None:
            raise RuntimeError("HTTP transport is not configured.")
        return _http_get_json(self._base_url, path, self._timeout)

    def _http_get_items(self, path: str) -> list[dict[str, Any]]:
        payload = self._http_get(path)
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise ValueError(f"Route {path} did not return an 'items' list.")
        return items

    def _http_post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self._base_url is None:
            raise RuntimeError("HTTP transport is not configured.")
        return _http_post_json(self._base_url, path, payload, self._timeout)
