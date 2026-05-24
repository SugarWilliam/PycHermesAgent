"""Structured office exports surfaced as sidecar artifacts."""

from __future__ import annotations

from pathlib import Path

from typing import Any

from pyc_hermes_agent.artifact_engine import ArtifactEngine
from pyc_hermes_agent.artifact_engine.office_export import export_pptx_bytes, export_xlsx_bytes
from pyc_hermes_agent.sidecar_api.services.common import _artifact_record_payload, _repo_root


def export_office_artifact_bundle(payload: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """

    Create a structured ``.xlsx`` / ``.pptx`` file under the runtime ``artifacts_dir``.

    Required JSON fields:

    - ``task_id`` (str)


    - ``format`` — ``xlsx`` | ``pptx``


    - ``spec`` — object passed to ``export_*_bytes``





    Optional:


    - ``filename`` — output file name (``.xlsx`` / ``.pptx`` enforced)

    """

    base = root or _repo_root()

    task_id_raw = payload.get("task_id")

    if not isinstance(task_id_raw, str) or not task_id_raw.strip():
        raise ValueError("Field 'task_id' is required.")

    fmt_raw = payload.get("format", "")

    if not isinstance(fmt_raw, str):
        raise ValueError("Field 'format' must be a string.")

    fmt = fmt_raw.strip().lower()

    spec = payload.get("spec")

    if not isinstance(spec, dict):
        raise ValueError("Field 'spec' must be an object.")

    engine = ArtifactEngine(root=base)

    name_raw = payload.get("filename")

    if fmt == "xlsx":
        data = export_xlsx_bytes(spec)

        default_name = "export.xlsx"

    elif fmt == "pptx":
        data = export_pptx_bytes(spec)
        default_name = "export.pptx"
    else:
        raise ValueError("Unsupported format; use 'xlsx' or 'pptx'.")

    filename = default_name
    if isinstance(name_raw, str) and name_raw.strip():
        candidate = name_raw.strip()
        lower = candidate.lower()
        if fmt == "xlsx" and not lower.endswith(".xlsx"):
            candidate = f"{candidate}.xlsx"
        if fmt == "pptx" and not lower.endswith(".pptx"):
            candidate = f"{candidate}.pptx"
        filename = candidate

    media = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if fmt == "xlsx"
        else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

    record = engine.export_bytes(task_id_raw.strip(), filename, data, media_type=media)

    return {"artifact": _artifact_record_payload(record), "format": fmt}


__all__ = ["export_office_artifact_bundle"]
