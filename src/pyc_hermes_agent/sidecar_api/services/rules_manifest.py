"""Ordered rules fingerprint manifest for Phase 3D external audit / export flows."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from pyc_hermes_agent.llm_gateway.rules import discover_ordered_rule_documents


def rules_manifest_bundle(workspace_root: Path) -> dict[str, Any]:
    docs = discover_ordered_rule_documents(workspace_root)
    items: list[dict[str, Any]] = []
    for order, doc_path in enumerate(docs):
        p = Path(doc_path)
        try:
            blob = p.read_bytes()
        except OSError:
            blob = b""
        digest = hashlib.sha256(blob).hexdigest() if blob else ""
        items.append(
            {
                "path": str(doc_path),
                "name": Path(doc_path).name,
                "precedence_order": order,
                "size_bytes": len(blob),
                "sha256": digest,
            }
        )
    return {
        "items": items,
        "workspace_root_hint": str(workspace_root.resolve()),
        "generated_at_unix": time.time(),
        "manifest_version": 1,
    }


__all__ = ["rules_manifest_bundle"]
