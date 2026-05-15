"""Minimal HTTP surface for MetaFramework v0.1."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple

from metaframework.service.facade import MetaFrameworkFacade


class _MetaFrameworkHTTPRequestHandler(BaseHTTPRequestHandler):
    facade = MetaFrameworkFacade()

    def _write_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json({"status": "ok", "service": "MetaFramework v0.1"})
            return
        if self.path == "/capabilities":
            self._write_json(self.facade.list_capabilities())
            return
        if self.path.startswith("/capabilities/"):
            capability_id = self.path.split("/capabilities/", 1)[1]
            try:
                self._write_json(self.facade.describe_capability(capability_id))
            except Exception as exc:
                self._write_json({"error": str(exc)}, status=404)
            return
        if self.path == "/snapshots":
            self._write_json(self.facade.list_snapshots())
            return
        if self.path.startswith("/snapshots/"):
            snapshot_id = self.path.split("/snapshots/", 1)[1]
            try:
                self._write_json(self.facade.load_snapshot(snapshot_id))
            except Exception as exc:
                self._write_json({"error": str(exc)}, status=404)
            return
        self._write_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/execute":
            self._write_json({"error": "Not found"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            request = json.loads(body.decode("utf-8"))
            result = self.facade.execute(request)
            self._write_json(result)
        except Exception as exc:  # pragma: no cover
            self._write_json({"error": str(exc)}, status=400)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def create_http_server(host: str = "127.0.0.1", port: int = 8010) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _MetaFrameworkHTTPRequestHandler)


def run_http_server(host: str = "127.0.0.1", port: int = 8010) -> None:
    server = create_http_server(host=host, port=port)
    print(f"MetaFramework v0.1 HTTP server listening on http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
