import json

import pytest

from pyc_hermes_agent.artifact_engine import ArtifactEngine
from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths


def test_artifact_engine_exports_text_and_json_under_artifacts_root(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)
    paths = ensure_runtime_directories(resolve_runtime_paths(tmp_path))

    summary = engine.export_text("task/1", "summary note.txt", "hello world")
    details = engine.export_json("task/1", "details.json", {"ok": True, "count": 2})

    assert paths.artifacts_dir in summary.path.parents
    assert paths.artifacts_dir in details.path.parents
    assert paths.mrag_dir not in summary.path.parents
    assert summary.path.read_text(encoding="utf-8") == "hello world"
    assert json.loads(details.path.read_text(encoding="utf-8"))["ok"] is True


def test_artifact_engine_lists_task_artifacts_and_builds_task_result_entries(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)
    first = engine.export_text("formal-analysis", "summary.txt", "done")
    second = engine.export_json("formal-analysis", "result.json", {"status": "ok"})

    records = engine.list_task_artifacts("formal-analysis")

    assert [record.artifact_id for record in records] == [first.artifact_id, second.artifact_id]
    assert records[0].as_task_artifact()["artifact_format_version"] == 1
    assert records[1].as_task_artifact()["media_type"] == "application/json"


def test_artifact_engine_rejects_tampered_metadata_format_version(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)
    record = engine.export_text("formal-analysis", "summary.txt", "done")
    metadata = _read_metadata(record.metadata_path)
    metadata["artifact_format_version"] = 999
    _write_metadata(record.metadata_path, metadata)

    with pytest.raises(ValueError, match="format version"):
        engine.list_task_artifacts("formal-analysis")


def test_artifact_engine_rejects_metadata_payload_path_outside_artifact_directory(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)
    record = engine.export_text("formal-analysis", "summary.txt", "done")
    metadata = _read_metadata(record.metadata_path)
    metadata["path"] = "../escape.txt"
    _write_metadata(record.metadata_path, metadata)

    with pytest.raises(ValueError, match="artifact directory"):
        engine.list_task_artifacts("formal-analysis")


def test_artifact_engine_rejects_metadata_payload_path_that_points_to_metadata_file(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)
    record = engine.export_text("formal-analysis", "summary.txt", "done")
    metadata = _read_metadata(record.metadata_path)
    metadata["path"] = "pyc_artifact.json"
    _write_metadata(record.metadata_path, metadata)

    with pytest.raises(ValueError, match="reserved metadata file"):
        engine.list_task_artifacts("formal-analysis")


def test_artifact_engine_rejects_export_payload_name_that_is_reserved_metadata_file(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)

    with pytest.raises(ValueError, match="reserved metadata file"):
        engine.export_text("formal-analysis", "pyc_artifact.json", "done")


def test_artifact_engine_rejects_metadata_for_missing_payload(tmp_path) -> None:
    engine = ArtifactEngine(root=tmp_path)
    record = engine.export_text("formal-analysis", "summary.txt", "done")
    record.path.unlink()

    with pytest.raises(ValueError, match="missing payload"):
        engine.list_task_artifacts("formal-analysis")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("size_bytes", 999, "size"),
        ("checksum", "sha256:" + "0" * 64, "checksum"),
    ),
)
def test_artifact_engine_rejects_metadata_payload_size_or_checksum_mismatch(
    tmp_path,
    field: str,
    value: object,
    message: str,
) -> None:
    engine = ArtifactEngine(root=tmp_path)
    record = engine.export_text("formal-analysis", "summary.txt", "done")
    metadata = _read_metadata(record.metadata_path)
    metadata[field] = value
    _write_metadata(record.metadata_path, metadata)

    with pytest.raises(ValueError, match=message):
        engine.list_task_artifacts("formal-analysis")


def _read_metadata(metadata_path):
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _write_metadata(metadata_path, metadata) -> None:
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
