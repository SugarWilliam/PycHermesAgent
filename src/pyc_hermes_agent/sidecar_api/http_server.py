"""Minimal local HTTP transport for the sidecar API."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any, Sequence, cast
from urllib.parse import unquote, urlparse
from uuid import uuid4

from pyc_hermes_agent.contracts import AgentLoopRequest, ChatCompletionRequest, MetaAnalysisRequest, RetrievalRequest
from pyc_hermes_agent.mrag_core import MRAGManifestIncompatibleError, MRAGStorageLockedError
from pyc_hermes_agent.sidecar_api.error_domains import (
    DOMAIN_ARTIFACT,
    DOMAIN_ASSET,
    DOMAIN_HERMES,
    DOMAIN_HTTP,
    DOMAIN_INTERNAL,
    DOMAIN_LLM,
    DOMAIN_META_HARNESS,
    DOMAIN_MRAG,
)
from pyc_hermes_agent.sidecar_api.logging import log_event
from pyc_hermes_agent.sidecar_api.service import (
    SIDECAR_API_VERSION,
    create_knowledge_base,
    get_config_snapshot,
    get_health,
    get_hermes_bridge_health,
    get_hermes_capability_snapshot,
    get_hermes_memory_snapshot,
    get_hermes_sessions_snapshot,
    get_hermes_skills_snapshot,
    get_hermes_tools_snapshot,
    get_meta_harness_benchmark_smoke,
    get_meta_harness_dependency_snapshot,
    get_meta_harness_value_proof_benchmark,
    get_runtime_paths_snapshot,
    ingest_file_document,
    ingest_text_document,
    ingest_url_document,
    invoke_chat_completion,
    invoke_formal_analysis,
    list_knowledge_bases,
    list_models,
    list_providers,
    list_asset_inventory,
    list_rules,
    list_sidecar_artifacts,
    list_skills,
    make_error_response,
    rebuild_mrag_chunk_index,
    run_agent_loop,
    search_knowledge_base,
    stream_agent_loop,
    stream_chat_completion,
)


_ARTIFACTS_PATTERN = re.compile(r"^/artifacts(?:/task/(.+))?$")

_KB_DOCUMENT_TEXT_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/documents/text$")
_KB_DOCUMENT_FILE_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/documents/file$")
_KB_DOCUMENT_URL_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/documents/url$")
_KB_SEARCH_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/search$")
_KB_REBUILD_INDEX_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/rebuild-index$")


def _get_or_bad_gateway(
    factory: Callable[[], dict[str, Any]],
    *,
    code: str,
    domain: str,
    details: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], HTTPStatus]:
    try:
        return factory(), HTTPStatus.OK
    except MRAGStorageLockedError:
        raise
    except MRAGManifestIncompatibleError:
        raise
    except Exception as exc:
        return (
            make_error_response(
                code,
                "runtime",
                str(exc),
                domain=domain,
                degraded=False,
                details=dict(details or {}),
            ),
            HTTPStatus.BAD_GATEWAY,
        )


class SidecarHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], *, root: Path | None = None) -> None:
        super().__init__(server_address, SidecarRequestHandler)
        self.root = root
        self._health_state_lock = Lock()
        self._last_health_status_label: str | None = None

    def remember_health_status(self, status_label: str) -> str | None:
        with self._health_state_lock:
            previous_status_label = self._last_health_status_label
            self._last_health_status_label = status_label
        return previous_status_label


class SidecarRequestHandler(BaseHTTPRequestHandler):
    server_version = f"PycHermesAgentSidecar/{SIDECAR_API_VERSION}"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._request_id = str(uuid4())
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def log_message(self, format: str, *args: object) -> None:
        return None

    def _dispatch(self, method: str) -> None:
        self._request_id = self._resolve_request_id()
        path = self._normalized_path()
        request_id = self._request_id
        log_event("http.request.started", request_id=request_id, method=method, path=path)
        try:
            if method == "GET":
                payload, status = self._handle_get(path)
            elif method == "POST":
                payload, status = self._handle_post(path, self._read_json_body())
            else:
                raise ValueError(f"Unsupported method: {method}")
        except json.JSONDecodeError as exc:
            payload = self._error_payload(
                "INVALID_JSON",
                "request",
                str(exc),
                domain=DOMAIN_HTTP,
                details={
                    "method": method,
                    "path": path,
                    "http_status": int(HTTPStatus.BAD_REQUEST),
                    "request_id": request_id,
                },
            )
            status = HTTPStatus.BAD_REQUEST
        except KeyError as exc:
            payload = self._error_payload(
                "NOT_FOUND",
                "transport",
                str(exc),
                domain=DOMAIN_HTTP,
                details={
                    "method": method,
                    "path": path,
                    "http_status": int(HTTPStatus.NOT_FOUND),
                    "request_id": request_id,
                },
            )
            status = HTTPStatus.NOT_FOUND
        except ValueError as exc:
            payload = self._error_payload(
                "INVALID_REQUEST",
                "request",
                str(exc),
                domain=DOMAIN_HTTP,
                details={
                    "method": method,
                    "path": path,
                    "http_status": int(HTTPStatus.BAD_REQUEST),
                    "request_id": request_id,
                },
            )
            status = HTTPStatus.BAD_REQUEST
        except MRAGStorageLockedError as exc:
            payload = self._error_payload(
                "MRAG_STORAGE_LOCKED",
                "storage",
                str(exc),
                domain=DOMAIN_MRAG,
                retryable=True,
                details={
                    "method": method,
                    "path": path,
                    "http_status": int(HTTPStatus.LOCKED),
                    "request_id": request_id,
                    "lock_path": str(exc.lock_path),
                },
            )
            status = HTTPStatus.LOCKED
        except MRAGManifestIncompatibleError as exc:
            payload = self._error_payload(
                "MRAG_MANIFEST_INCOMPATIBLE",
                "storage",
                str(exc),
                domain=DOMAIN_MRAG,
                retryable=False,
                details={
                    "method": method,
                    "path": path,
                    "http_status": int(HTTPStatus.BAD_GATEWAY),
                    "request_id": request_id,
                    "knowledge_base_id": exc.knowledge_base_id,
                },
            )
            status = HTTPStatus.BAD_GATEWAY
        except Exception as exc:  # pragma: no cover - defensive boundary
            payload = self._error_payload(
                "INTERNAL_ERROR",
                "internal",
                str(exc),
                domain=DOMAIN_INTERNAL,
                details={
                    "method": method,
                    "path": path,
                    "http_status": int(HTTPStatus.INTERNAL_SERVER_ERROR),
                    "request_id": request_id,
                },
            )
            status = HTTPStatus.INTERNAL_SERVER_ERROR

        if payload is None:
            log_event(
                "http.request.finished",
                request_id=request_id,
                method=method,
                path=path,
                status=int(status),
                has_error=False,
            )
            return
        error = payload.get("error") if isinstance(payload, dict) else None
        log_event(
            "http.request.finished",
            request_id=request_id,
            method=method,
            path=path,
            status=int(status),
            has_error="error" in payload,
            error_code=error.get("code") if isinstance(error, dict) else None,
            error_category=error.get("category") if isinstance(error, dict) else None,
            error_domain=error.get("domain") if isinstance(error, dict) else None,
        )
        if isinstance(payload, dict):
            self._ensure_error_correlates_request(payload, request_id)
        self._write_json(status, payload)

    def _handle_get(self, path: str) -> tuple[dict[str, Any], HTTPStatus]:
        root = self._server_root()

        if path == "/":
            try:
                health = get_health(root)
                return {
                    "service": "pyc-hermes-agent-sidecar",
                    "version": health["version"],
                    "sidecar_api_version": health["sidecar_api_version"],
                    "routes": [
                        "/health",
                        "/runtime-paths",
                        "/config",
                        "/providers",
                        "/models",
                        "/rules",
                        "/skills",
                        "/assets",
                        "/artifacts",
                        "/artifacts/task/{task_id}",
                        "/hermes/capability",
                        "/hermes/bridge-health",
                        "/hermes/sessions",
                        "/hermes/memory",
                        "/hermes/skills",
                        "/hermes/tools",
                        "/agent/run",
                        "/agent/run/stream",
                        "/llm/chat",
                        "/llm/chat/stream",
                        "/formal-analysis",
                        "/meta-harness/dependencies",
                        "/meta-harness/benchmark-smoke",
                        "/meta-harness/value-proof",
                        "/knowledge-bases",
                        "/knowledge-bases/{id}/documents/text",
                        "/knowledge-bases/{id}/documents/file",
                        "/knowledge-bases/{id}/documents/url",
                        "/knowledge-bases/{id}/search",
                        "/knowledge-bases/{id}/rebuild-index",
                    ],
                }, HTTPStatus.OK
            except Exception as exc:
                return (
                    make_error_response(
                        "HEALTH_SNAPSHOT_FAILED",
                        "runtime",
                        str(exc),
                        domain=DOMAIN_INTERNAL,
                        degraded=False,
                        details={"path": "/"},
                    ),
                    HTTPStatus.BAD_GATEWAY,
                )
        if path == "/health":
            try:
                health = get_health(root)
                self._log_health_transition(health)
                return health, HTTPStatus.OK
            except Exception as exc:
                return (
                    make_error_response(
                        "HEALTH_SNAPSHOT_FAILED",
                        "runtime",
                        str(exc),
                        domain=DOMAIN_INTERNAL,
                        degraded=False,
                        details={"path": "/health"},
                    ),
                    HTTPStatus.BAD_GATEWAY,
                )
        if path == "/runtime-paths":
            return _get_or_bad_gateway(
                lambda: get_runtime_paths_snapshot(root),
                code="RUNTIME_PATHS_SNAPSHOT_FAILED",
                domain=DOMAIN_INTERNAL,
                details={},
            )
        if path == "/config":
            return _get_or_bad_gateway(
                lambda: get_config_snapshot(root),
                code="CONFIG_SNAPSHOT_FAILED",
                domain=DOMAIN_INTERNAL,
                details={},
            )
        if path == "/providers":
            return _get_or_bad_gateway(
                lambda: {"items": list_providers(root)},
                code="PROVIDER_LIST_FAILED",
                domain=DOMAIN_INTERNAL,
                details={},
            )
        if path == "/models":
            return _get_or_bad_gateway(
                lambda: {"items": list_models(root)},
                code="MODEL_LIST_FAILED",
                domain=DOMAIN_LLM,
                details={},
            )
        if path == "/rules":
            return _get_or_bad_gateway(
                lambda: {"items": list_rules(root)},
                code="RULE_LIST_FAILED",
                domain=DOMAIN_INTERNAL,
                details={},
            )
        if path == "/skills":
            return _get_or_bad_gateway(
                lambda: {"items": list_skills(root)},
                code="SKILL_LIST_FAILED",
                domain=DOMAIN_INTERNAL,
                details={},
            )
        if path == "/assets":
            return _get_or_bad_gateway(
                lambda: list_asset_inventory(root),
                code="ASSET_INVENTORY_FAILED",
                domain=DOMAIN_ASSET,
                details={},
            )
        artifacts_match = _ARTIFACTS_PATTERN.fullmatch(path)
        if artifacts_match:
            raw_task = artifacts_match.group(1)
            task_id = unquote(raw_task) if raw_task else None
            return _get_or_bad_gateway(
                lambda: list_sidecar_artifacts(root, task_id=task_id),
                code="ARTIFACT_LIST_FAILED",
                domain=DOMAIN_ARTIFACT,
                details={"task_id": task_id} if task_id else {},
            )
        if path == "/hermes/capability":
            return _get_or_bad_gateway(
                lambda: get_hermes_capability_snapshot(root),
                code="HERMES_SNAPSHOT_FAILED",
                domain=DOMAIN_HERMES,
                details={"hermes_surface": "capability"},
            )
        if path == "/hermes/bridge-health":
            return _get_or_bad_gateway(
                lambda: get_hermes_bridge_health(root),
                code="HERMES_SNAPSHOT_FAILED",
                domain=DOMAIN_HERMES,
                details={"hermes_surface": "bridge-health"},
            )
        if path == "/hermes/sessions":
            return _get_or_bad_gateway(
                lambda: get_hermes_sessions_snapshot(root),
                code="HERMES_SNAPSHOT_FAILED",
                domain=DOMAIN_HERMES,
                details={"hermes_surface": "sessions"},
            )
        if path == "/hermes/memory":
            return _get_or_bad_gateway(
                lambda: get_hermes_memory_snapshot(root),
                code="HERMES_SNAPSHOT_FAILED",
                domain=DOMAIN_HERMES,
                details={"hermes_surface": "memory"},
            )
        if path == "/hermes/skills":
            return _get_or_bad_gateway(
                lambda: get_hermes_skills_snapshot(root),
                code="HERMES_SNAPSHOT_FAILED",
                domain=DOMAIN_HERMES,
                details={"hermes_surface": "skills"},
            )
        if path == "/hermes/tools":
            return _get_or_bad_gateway(
                lambda: get_hermes_tools_snapshot(root),
                code="HERMES_SNAPSHOT_FAILED",
                domain=DOMAIN_HERMES,
                details={"hermes_surface": "tools"},
            )
        if path == "/meta-harness/dependencies":
            return _get_or_bad_gateway(
                lambda: get_meta_harness_dependency_snapshot(),
                code="META_HARNESS_DEPENDENCY_SNAPSHOT_FAILED",
                domain=DOMAIN_META_HARNESS,
                details={},
            )
        if path == "/knowledge-bases":
            return _get_or_bad_gateway(
                lambda: {"items": list_knowledge_bases(root)},
                code="MRAG_KNOWLEDGE_BASE_LIST_FAILED",
                domain=DOMAIN_MRAG,
                details={},
            )
        raise KeyError(f"Unknown route: {path}")

    def _handle_post(self, path: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, HTTPStatus]:
        if path == "/formal-analysis":
            response = invoke_formal_analysis(MetaAnalysisRequest(**payload))
            status = HTTPStatus.OK if "error" not in response else HTTPStatus.BAD_GATEWAY
            return response, status
        if path == "/meta-harness/benchmark-smoke":
            return _get_or_bad_gateway(
                lambda: get_meta_harness_benchmark_smoke(),
                code="META_HARNESS_BENCHMARK_FAILED",
                domain=DOMAIN_META_HARNESS,
                details={"benchmark_kind": "smoke"},
            )
        if path == "/meta-harness/value-proof":
            return _get_or_bad_gateway(
                lambda: get_meta_harness_value_proof_benchmark(),
                code="META_HARNESS_BENCHMARK_FAILED",
                domain=DOMAIN_META_HARNESS,
                details={"benchmark_kind": "value_proof"},
            )
        if path == "/agent/run":
            response = run_agent_loop(AgentLoopRequest(**payload), root=self._server_root())
            status = HTTPStatus.OK if "error" not in response else HTTPStatus.BAD_GATEWAY
            return response, status
        if path == "/agent/run/stream":
            self._write_sse(stream_agent_loop(AgentLoopRequest(**payload), root=self._server_root()))
            return None, HTTPStatus.OK
        if path == "/llm/chat":
            response = invoke_chat_completion(ChatCompletionRequest(**payload), root=self._server_root())
            status = HTTPStatus.OK if "error" not in response else HTTPStatus.BAD_GATEWAY
            return response, status
        if path == "/llm/chat/stream":
            self._write_sse(stream_chat_completion(ChatCompletionRequest(**payload), root=self._server_root()))
            return None, HTTPStatus.OK
        if path == "/knowledge-bases":
            name = payload.get("name", "")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Field 'name' is required.")
            return create_knowledge_base(name=name.strip(), root=self._server_root()), HTTPStatus.CREATED

        rebuild_match = _KB_REBUILD_INDEX_PATTERN.fullmatch(path)
        if rebuild_match:
            knowledge_base_id = unquote(rebuild_match.group(1))
            return rebuild_mrag_chunk_index(knowledge_base_id, root=self._server_root()), HTTPStatus.OK

        document_match = _KB_DOCUMENT_TEXT_PATTERN.fullmatch(path)
        if document_match:
            knowledge_base_id = unquote(document_match.group(1))
            text = payload.get("text", "")
            if not isinstance(text, str) or not text:
                raise ValueError("Field 'text' is required.")
            title = payload.get("title", "")
            source_uri = payload.get("source_uri", "")
            source_type = payload.get("source_type", "text")
            return (
                ingest_text_document(
                    knowledge_base_id,
                    text,
                    title=title if isinstance(title, str) else "",
                    source_uri=source_uri if isinstance(source_uri, str) else "",
                    source_type=source_type if isinstance(source_type, str) else "text",
                    root=self._server_root(),
                ),
                HTTPStatus.CREATED,
            )

        file_match = _KB_DOCUMENT_FILE_PATTERN.fullmatch(path)
        if file_match:
            knowledge_base_id = unquote(file_match.group(1))
            raw_path = payload.get("path", "")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("Field 'path' is required.")
            return (
                ingest_file_document(
                    knowledge_base_id,
                    raw_path.strip(),
                    root=self._server_root(),
                ),
                HTTPStatus.CREATED,
            )

        url_match = _KB_DOCUMENT_URL_PATTERN.fullmatch(path)
        if url_match:
            knowledge_base_id = unquote(url_match.group(1))
            url = payload.get("url", "")
            text = payload.get("text", "")
            title = payload.get("title", "")
            if not isinstance(url, str) or not url.strip():
                raise ValueError("Field 'url' is required.")
            if not isinstance(text, str) or not text:
                raise ValueError("Field 'text' is required.")
            return (
                ingest_url_document(
                    knowledge_base_id,
                    url.strip(),
                    text,
                    title=title if isinstance(title, str) else "",
                    root=self._server_root(),
                ),
                HTTPStatus.CREATED,
            )

        search_match = _KB_SEARCH_PATTERN.fullmatch(path)
        if search_match:
            knowledge_base_id = unquote(search_match.group(1))
            return search_knowledge_base(knowledge_base_id, RetrievalRequest(**payload), root=self._server_root()), HTTPStatus.OK

        raise KeyError(f"Unknown route: {path}")

    def _normalized_path(self) -> str:
        path = urlparse(self.path).path.rstrip("/")
        return path or "/"

    def _resolve_request_id(self) -> str:
        incoming = self.headers.get("X-Pyc-Request-Id", "").strip()
        if incoming and len(incoming) <= 128:
            return incoming
        return self._request_id

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length)
        payload = json.loads(raw_body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON request body must be an object.")
        return payload

    def _server_root(self) -> Path | None:
        return cast(SidecarHTTPServer, self.server).root

    def _log_health_transition(self, health: dict[str, Any]) -> None:
        status_label = health.get("status_label")
        if not isinstance(status_label, str) or not status_label:
            return
        previous_status_label = cast(SidecarHTTPServer, self.server).remember_health_status(status_label)
        if previous_status_label == status_label:
            return
        log_event(
            "sidecar.health.transition",
            request_id=self._request_id,
            previous_status_label=previous_status_label,
            status_label=status_label,
            degraded=bool(health.get("degraded")),
        )

    def _ensure_error_correlates_request(self, payload: dict[str, Any], request_id: str) -> None:
        """Attach ``request_id`` to error envelopes returned by the service layer or transport."""
        err = payload.get("error")
        if not isinstance(err, dict):
            return
        details = err.get("details")
        if not isinstance(details, dict):
            details = {}
            err["details"] = details
        details.setdefault("request_id", request_id)

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Pyc-Sidecar-Api-Version", SIDECAR_API_VERSION)
        self.send_header("X-Pyc-Request-Id", self._request_id)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_sse(self, events) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("X-Pyc-Sidecar-Api-Version", SIDECAR_API_VERSION)
        self.send_header("X-Pyc-Request-Id", self._request_id)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for event in events:
            payload = asdict(event) if is_dataclass(event) else event
            if not isinstance(payload, dict):
                continue
            payload.setdefault("request_id", self._request_id)
            body = f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            self.wfile.write(body)
            self.wfile.flush()

    @staticmethod
    def _error_payload(
        code: str,
        category: str,
        message: str,
        *,
        domain: str = DOMAIN_INTERNAL,
        retryable: bool = False,
        degraded: bool = False,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return make_error_response(
            code,
            category,
            message,
            domain=domain,
            retryable=retryable,
            degraded=degraded,
            details=details,
        )


def create_http_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    root: Path | None = None,
) -> SidecarHTTPServer:
    return SidecarHTTPServer((host, port), root=root)


def serve_http(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    root: Path | None = None,
) -> None:
    server = create_http_server(host=host, port=port, root=root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PycHermesAgent local sidecar HTTP server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", default="")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    serve_http(host=args.host, port=args.port, root=root)
    return 0


__all__ = ["SidecarHTTPServer", "build_argument_parser", "create_http_server", "main", "serve_http"]


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    raise SystemExit(main())
