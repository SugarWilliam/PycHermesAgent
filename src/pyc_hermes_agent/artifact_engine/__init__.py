"""Local-first artifact export helpers."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths

_ARTIFACT_FORMAT_VERSION = 1
_ARTIFACT_METADATA_FILENAME = "pyc_artifact.json"


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    task_id: str
    name: str
    media_type: str
    path: Path
    metadata_path: Path
    size_bytes: int
    checksum: str
    created_at_ns: int
    artifact_format_version: int = _ARTIFACT_FORMAT_VERSION

    def as_task_artifact(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "media_type": self.media_type,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "artifact_format_version": self.artifact_format_version,
        }


class ArtifactEngine:
    def __init__(self, *, root: Path | None = None) -> None:
        self._paths = ensure_runtime_directories(resolve_runtime_paths(root))

    @property
    def artifacts_dir(self) -> Path:
        return self._paths.artifacts_dir

    def export_bytes(
        self,
        task_id: str,
        name: str,
        payload: bytes,
        *,
        media_type: str,
        artifact_id: str | None = None,
    ) -> ArtifactRecord:
        storage_task_id = _sanitize_segment(task_id, fallback="task")
        storage_name = _sanitize_segment(name, fallback="artifact.bin")
        _reject_reserved_payload_name(storage_name)
        storage_artifact_id = _sanitize_segment(artifact_id or uuid4().hex, fallback=uuid4().hex)
        target_dir = self.artifacts_dir / storage_task_id / storage_artifact_id
        if target_dir.exists():
            raise FileExistsError(f"Artifact already exists: {target_dir}")

        staging_dir = self.artifacts_dir / ".staging" / uuid4().hex
        checksum = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        created_at_ns = time.time_ns()
        metadata = {
            "artifact_format_version": _ARTIFACT_FORMAT_VERSION,
            "artifact_id": storage_artifact_id,
            "task_id": task_id,
            "name": storage_name,
            "media_type": media_type,
            "path": storage_name,
            "size_bytes": len(payload),
            "checksum": checksum,
            "created_at_ns": created_at_ns,
        }

        try:
            staging_dir.mkdir(parents=True, exist_ok=False)
            (staging_dir / storage_name).write_bytes(payload)
            (staging_dir / _ARTIFACT_METADATA_FILENAME).write_text(
                json.dumps(metadata, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            staging_dir.replace(target_dir)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

        return ArtifactRecord(
            artifact_id=storage_artifact_id,
            task_id=task_id,
            name=storage_name,
            media_type=media_type,
            path=target_dir / storage_name,
            metadata_path=target_dir / _ARTIFACT_METADATA_FILENAME,
            size_bytes=len(payload),
            checksum=checksum,
            created_at_ns=created_at_ns,
        )

    def export_text(
        self,
        task_id: str,
        name: str,
        content: str,
        *,
        media_type: str = "text/plain; charset=utf-8",
        artifact_id: str | None = None,
    ) -> ArtifactRecord:
        return self.export_bytes(
            task_id,
            name,
            content.encode("utf-8"),
            media_type=media_type,
            artifact_id=artifact_id,
        )

    def export_json(
        self,
        task_id: str,
        name: str,
        payload: object,
        *,
        artifact_id: str | None = None,
    ) -> ArtifactRecord:
        serialized = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
        return self.export_bytes(
            task_id,
            name,
            serialized,
            media_type="application/json",
            artifact_id=artifact_id,
        )

    def list_task_artifacts(self, task_id: str) -> list[ArtifactRecord]:
        storage_task_id = _sanitize_segment(task_id, fallback="task")
        task_dir = self.artifacts_dir / storage_task_id
        if not task_dir.exists():
            return []

        records: list[ArtifactRecord] = []
        for metadata_path in sorted(task_dir.glob(f"*/{_ARTIFACT_METADATA_FILENAME}")):
            records.append(_read_artifact_record(metadata_path))
        return sorted(records, key=lambda record: (record.created_at_ns, record.artifact_id))

    def list_all_artifacts(self) -> list[ArtifactRecord]:
        """List artifact records for every task directory under ``artifacts_dir``."""
        root = self.artifacts_dir
        if not root.exists():
            return []

        records: list[ArtifactRecord] = []
        for metadata_path in sorted(root.glob(f"*/*/{_ARTIFACT_METADATA_FILENAME}")):
            if ".staging" in metadata_path.parts:
                continue
            try:
                records.append(_read_artifact_record(metadata_path))
            except ValueError:
                continue
        return sorted(records, key=lambda record: (record.created_at_ns, record.artifact_id))


def _sanitize_segment(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip("._-")
    if not cleaned:
        return fallback
    return cleaned


def _read_artifact_record(metadata_path: Path) -> ArtifactRecord:
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    artifact_dir = metadata_path.parent.resolve()

    format_version = int(payload["artifact_format_version"])
    if format_version != _ARTIFACT_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported artifact format version in {metadata_path}: "
            f"expected {_ARTIFACT_FORMAT_VERSION}, got {format_version}"
        )

    relative_payload_path = Path(str(payload["path"]))
    if relative_payload_path.is_absolute():
        raise ValueError(f"Artifact metadata payload path is outside artifact directory: {metadata_path}")
    if relative_payload_path.as_posix() == _ARTIFACT_METADATA_FILENAME:
        raise ValueError(f"Artifact metadata payload path uses reserved metadata file: {_ARTIFACT_METADATA_FILENAME}")
    payload_path = (artifact_dir / relative_payload_path).resolve()
    if not payload_path.is_relative_to(artifact_dir):
        raise ValueError(f"Artifact metadata payload path is outside artifact directory: {metadata_path}")
    if not payload_path.is_file():
        raise ValueError(f"Artifact metadata references missing payload: {payload_path}")

    size_bytes = int(payload["size_bytes"])
    actual_size = payload_path.stat().st_size
    if actual_size != size_bytes:
        raise ValueError(
            f"Artifact metadata payload size mismatch for {payload_path}: expected {size_bytes}, got {actual_size}"
        )

    checksum = str(payload["checksum"])
    actual_checksum = _calculate_file_checksum(payload_path)
    if actual_checksum != checksum:
        raise ValueError(
            f"Artifact metadata payload checksum mismatch for {payload_path}: expected {checksum}, got {actual_checksum}"
        )

    return ArtifactRecord(
        artifact_id=str(payload["artifact_id"]),
        task_id=str(payload["task_id"]),
        name=str(payload["name"]),
        media_type=str(payload["media_type"]),
        path=payload_path,
        metadata_path=metadata_path,
        size_bytes=size_bytes,
        checksum=checksum,
        created_at_ns=int(payload.get("created_at_ns", 0)),
        artifact_format_version=format_version,
    )


def _calculate_file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                return f"sha256:{digest.hexdigest()}"
            digest.update(chunk)


def _reject_reserved_payload_name(name: str) -> None:
    if name == _ARTIFACT_METADATA_FILENAME:
        raise ValueError(f"Artifact payload name uses reserved metadata file: {_ARTIFACT_METADATA_FILENAME}")


__all__ = ["ArtifactEngine", "ArtifactRecord"]
