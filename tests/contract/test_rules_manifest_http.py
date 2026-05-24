"""Phase 3D — rules manifest fingerprint export."""

from __future__ import annotations

from pathlib import Path

from tests.contract.test_sidecar_http import _get_json, _start_server


def test_sidecar_get_rules_manifest_shape(tmp_path: Path) -> None:
    srv, _thr = _start_server(root=tmp_path)

    _, port = srv.server_address[:2]

    base = f"http://127.0.0.1:{port}"
    status, body = _get_json(f"{base}/rules/manifest")

    srv.shutdown()

    assert status == 200
    assert body.get("manifest_version") == 1
    assert "items" in body and isinstance(body["items"], list)
    assert "generated_at_unix" in body

