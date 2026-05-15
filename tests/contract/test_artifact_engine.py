import json

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
