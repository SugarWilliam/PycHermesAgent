"""Phase 3D — persisted user skills under writable runtime."""

from __future__ import annotations

from pathlib import Path

from tests.contract.test_sidecar_http import _get_json, _post_json, _start_server


def test_sidecar_post_skills_user_lists_user_local_skill(tmp_path: Path) -> None:
    srv, _thr = _start_server(root=tmp_path)

    _, port = srv.server_address[:2]

    base = f"http://127.0.0.1:{port}"

    skill_md = """---
name: contract-user-skill-x
description: Contract-published skill
---

### Scope
Minimal smoke.
"""

    posted, bundle = _post_json(
        f"{base}/skills/user",
        {"skill_id": "contract-user-skill-x", "markdown": skill_md},
    )

    assert posted == 201
    assert bundle.get("skill_id") == "contract-user-skill-x"

    _, listed = _get_json(f"{base}/skills")
    srv.shutdown()

    row = next((i for i in listed.get("items", []) if i.get("id") == "contract-user-skill-x"), None)
    assert row is not None
    assert row.get("source_kind") == "user_local"
