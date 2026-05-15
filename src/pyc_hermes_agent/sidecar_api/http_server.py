"""Minimal local HTTP transport for the sidecar API."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence, cast
from urllib.parse import unquote, urlparse

from pyc_hermes_agent.contracts import AgentLoopRequest, ChatCompletionRequest, MetaAnalysisRequest, RetrievalRequest
from pyc_hermes_agent.sidecar_api.logging import log_event
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


_KB_DOCUMENT_TEXT_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/documents/text$")
_KB_SEARCH_PATTERN = re.compile(r"^/knowledge-bases/([^/]+)/search$")


class SidecarHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], *, root: Path | None = None) -> None:
        super().__init__(server_address, SidecarRequestHandler)
        self.root = root


class SidecarRequestHandler(BaseHTTPRequestHandler):
    server_version = "PycHermesAgentSidecar/0.1"

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def log_message(self, format: str, *args: object) -> None:
        return None

    def _dispatch(self, method: str) -> None:
        path = self._normalized_path()
        log_event("http.request.started", method=method, path=path)
        try:
            if method == "GET":
                payload, status = self._handle_get(path)
            elif method == "POST":
                payload, status = self._handle_post(path, self._read_json_body())
            else:
                raise ValueError(f"Unsupported method: {method}")
        except json.JSONDecodeError as exc:
            payload = self._error_payload("INVALID_JSON", str(exc))
            status = HTTPStatus.BAD_REQUEST
        except KeyError as exc:
            payload = self._error_payload("NOT_FOUND", str(exc))
            status = HTTPStatus.NOT_FOUND
        except ValueError as exc:
            payload = self._error_payload("INVALID_REQUEST", str(exc))
            status = HTTPStatus.BAD_REQUEST
        except Exception as exc:  # pragma: no cover - defensive boundary
            payload = self._error_payload("INTERNAL_ERROR", str(exc))
            status = HTTPStatus.INTERNAL_SERVER_ERROR

        if payload is None:
            log_event("http.request.finished", method=method, path=path, status=int(status), has_error=False)
            return
        log_event("http.request.finished", method=method, path=path, status=int(status), has_error="error" in payload)
        self._write_json(status, payload)

    def _handle_get(self, path: str) -> tuple[dict[str, Any], HTTPStatus]:
        root = self._server_root()

        if path == "/":
            health = get_health(root)
            return {
                "service": "pyc-hermes-agent-sidecar",
                "version": health["version"],
                "sidecar_api_version": health["sidecar_api_version"],
                "routes": [
                    "/health",
                    "/config",
                    "/providers",
                    "/models",
                    "/rules",
                    "/skills",
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
                    "/knowledge-bases",
                    "/knowledge-bases/{id}/documents/text",
                    "/knowledge-bases/{id}/search",
                ],
            }, HTTPStatus.OK
        if path == "/health":
            return get_health(root), HTTPStatus.OK
        if path == "/config":
            return get_config_snapshot(root), HTTPStatus.OK
        if path == "/providers":
            return {"items": list_providers(root)}, HTTPStatus.OK
        if path == "/models":
            return {"items": list_models(root)}, HTTPStatus.OK
        if path == "/rules":
            return {"items": list_rules(root)}, HTTPStatus.OK
        if path == "/skills":
            return {"items": list_skills(root)}, HTTPStatus.OK
        if path == "/hermes/capability":
            return get_hermes_capability_snapshot(root), HTTPStatus.OK
        if path == "/hermes/bridge-health":
            return get_hermes_bridge_health(root), HTTPStatus.OK
        if path == "/hermes/sessions":
            return get_hermes_sessions_snapshot(root), HTTPStatus.OK
        if path == "/hermes/memory":
            return get_hermes_memory_snapshot(root), HTTPStatus.OK
        if path == "/hermes/skills":
            return get_hermes_skills_snapshot(root), HTTPStatus.OK
        if path == "/hermes/tools":
            return get_hermes_tools_snapshot(root), HTTPStatus.OK
        if path == "/knowledge-bases":
            return {"items": list_knowledge_bases(root)}, HTTPStatus.OK
        raise KeyError(f"Unknown route: {path}")

    def _handle_post(self, path: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, HTTPStatus]:
        if path == "/formal-analysis":
            return invoke_formal_analysis(MetaAnalysisRequest(**payload)), HTTPStatus.OK
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

        search_match = _KB_SEARCH_PATTERN.fullmatch(path)
        if search_match:
            knowledge_base_id = unquote(search_match.group(1))
            return search_knowledge_base(knowledge_base_id, RetrievalRequest(**payload), root=self._server_root()), HTTPStatus.OK

        raise KeyError(f"Unknown route: {path}")

    def _normalized_path(self) -> str:
        path = urlparse(self.path).path.rstrip("/")
        return path or "/"

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

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_sse(self, events) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for event in events:
            payload = asdict(event) if is_dataclass(event) else event
            if not isinstance(payload, dict):
                continue
            body = f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            self.wfile.write(body)
            self.wfile.flush()

    @staticmethod
    def _error_payload(code: str, message: str, *, status: str = "error") -> dict[str, Any]:
        return {"status": status, "error": {"code": code, "message": message}}


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
