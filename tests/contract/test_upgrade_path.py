"""Verify data directory compatibility across version upgrades.

Simulates v0.2.1 → v0.3.0 upgrade by creating v0.2.1-style data files
and verifying the current code can read them correctly.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyc_hermes_agent.common.runtime_paths import resolve_runtime_paths
from pyc_hermes_agent.hermes_engine.memory import UserPreferences
from pyc_hermes_agent.mrag_core.persistence import (
    load_knowledge_bases,
)
from pyc_hermes_agent.mrag_core.migrate import plan_migrations


# --- v0.2.1 fixtures ---

V021_PREFERENCES = {
    "language": "zh",
    "preferred_output_style": "brief",
    "domain_hints": ["embedded", "networking"],
    "custom_instructions": "Always cite sources.",
}

V021_MANIFEST = {
    "manifest_version": 1,
    "index_format_version": 1,
    "knowledge_base_id": "kb_legacy",
    "name": "Legacy KB",
    "document_count": 1,
    "chunk_count": 2,
}

V021_DOCUMENT = {
    "schema_version": "1.0",
    "document_id": "doc_001",
    "title": "Old doc",
    "source_type": "text",
    "source_uri": "file:///tmp/old.txt",
    "text": "Hello from v0.2.1",
    "metadata": {},
}

V021_CHUNKS_JSON = {
    "index_format_version": 1,
    "chunks": [
        {
            "schema_version": "1.0",
            "chunk_id": "c1",
            "document_id": "doc_001",
            "index": 0,
            "text": "Hello from",
            "metadata": {},
        },
        {
            "schema_version": "1.0",
            "chunk_id": "c2",
            "document_id": "doc_001",
            "index": 1,
            "text": "v0.2.1",
            "metadata": {},
        },
    ],
}


def _create_v021_mrag_layout(storage_root: Path) -> None:
    """Create a v0.2.1-style MRAG storage tree."""
    kb_dir = storage_root / "knowledge_bases" / "kb_legacy"
    kb_dir.mkdir(parents=True)
    (kb_dir / "manifest.json").write_text(json.dumps(V021_MANIFEST), encoding="utf-8")

    sources_dir = storage_root / "sources" / "kb_legacy"
    sources_dir.mkdir(parents=True)
    (sources_dir / "doc_001.json").write_text(json.dumps(V021_DOCUMENT), encoding="utf-8")

    indexes_dir = storage_root / "indexes" / "kb_legacy"
    indexes_dir.mkdir(parents=True)
    (indexes_dir / "chunks.json").write_text(json.dumps(V021_CHUNKS_JSON), encoding="utf-8")


# --- Tests ---


def test_preferences_v021_format_readable(tmp_path: Path) -> None:
    """A preferences.json from v0.2.1 is readable by current UserPreferences.load()."""
    pref_file = tmp_path / "config" / "preferences.json"
    pref_file.parent.mkdir(parents=True)
    pref_file.write_text(json.dumps(V021_PREFERENCES), encoding="utf-8")

    prefs = UserPreferences.load(pref_file)

    assert prefs.language == "zh"
    assert prefs.preferred_output_style == "brief"
    assert prefs.domain_hints == ["embedded", "networking"]
    assert prefs.custom_instructions == "Always cite sources."


def test_mrag_json_storage_still_readable(tmp_path: Path) -> None:
    """MRAG JSON storage from v0.2.1 can still be read."""
    _create_v021_mrag_layout(tmp_path)

    kbs = load_knowledge_bases(tmp_path)

    assert "kb_legacy" in kbs
    kb = kbs["kb_legacy"]
    assert kb.name == "Legacy KB"
    assert len(kb.documents) == 1
    assert len(kb.chunks) == 2
    assert kb.chunks[0].text == "Hello from"
    assert kb.chunks[1].text == "v0.2.1"


def test_mrag_manifest_v1_compatible(tmp_path: Path) -> None:
    """A manifest_version=1 knowledge base is accepted by current runtime."""
    _create_v021_mrag_layout(tmp_path)

    kbs = load_knowledge_bases(tmp_path)

    assert "kb_legacy" in kbs


def test_new_fields_have_defaults(tmp_path: Path) -> None:
    """New fields added in v0.3.0 have sensible defaults when reading v0.2.1 data."""
    # v0.2.1 preferences lack analysis_conservatism
    pref_file = tmp_path / "preferences.json"
    pref_file.write_text(json.dumps(V021_PREFERENCES), encoding="utf-8")

    prefs = UserPreferences.load(pref_file)

    # analysis_conservatism was added; v0.2.1 data won't have it → default applied
    assert prefs.analysis_conservatism == "moderate"


def test_sqlite_db_absent_graceful(tmp_path: Path) -> None:
    """Current code handles KB directories without chunks.db gracefully."""
    _create_v021_mrag_layout(tmp_path)

    # Ensure no SQLite file exists
    sqlite_path = tmp_path / "indexes" / "kb_legacy" / "chunks.db"
    assert not sqlite_path.exists()

    # Loading should work fine with only JSON
    kbs = load_knowledge_bases(tmp_path)
    assert "kb_legacy" in kbs
    assert len(kbs["kb_legacy"].chunks) == 2


def test_runtime_paths_stable_across_versions(tmp_path: Path) -> None:
    """Runtime path resolution produces consistent paths."""
    paths = resolve_runtime_paths(root=tmp_path)

    # Verify structural layout matches expected v0.2.1 pattern
    sandbox = tmp_path.resolve() / ".pyc_hermes_agent_runtime"
    assert paths.config_dir == sandbox / "APPDATA" / "PycHermesAgent"
    assert paths.local_data_dir == sandbox / "LOCALAPPDATA" / "PycHermesAgent"
    assert paths.mrag_dir == paths.local_data_dir / "mrag_core"
    assert paths.logs_dir == paths.local_data_dir / "logs"
    assert paths.cache_dir == paths.local_data_dir / "cache"
    assert paths.indexes_dir == paths.local_data_dir / "indexes"
    assert paths.models_dir == paths.local_data_dir / "models"
    assert paths.artifacts_dir == paths.local_data_dir / "artifacts"


def test_migrate_planner_reports_v1_as_ok(tmp_path: Path) -> None:
    """Migration planner accepts v0.2.1 storage as current (no upgrade blocked)."""
    _create_v021_mrag_layout(tmp_path)

    notes = plan_migrations(tmp_path)

    assert any("ok" in n and "kb_legacy" in n for n in notes)
    assert not any(n.startswith("blocked:") for n in notes)
