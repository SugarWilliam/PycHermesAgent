from pyc_hermes_agent import ensure_runtime_directories, resolve_runtime_paths


def test_runtime_paths_follow_sandbox_layout_when_root_is_overridden(tmp_path) -> None:
    paths = ensure_runtime_directories(resolve_runtime_paths(tmp_path))

    assert paths.config_dir == tmp_path / ".pyc_hermes_agent_runtime" / "APPDATA" / "PycHermesAgent"
    assert paths.local_data_dir == tmp_path / ".pyc_hermes_agent_runtime" / "LOCALAPPDATA" / "PycHermesAgent"
    assert paths.logs_dir.exists()
    assert paths.cache_dir.exists()
    assert paths.indexes_dir.exists()
    assert paths.models_dir.exists()
    assert paths.artifacts_dir.exists()
    assert paths.mrag_dir.exists()
