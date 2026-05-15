from pathlib import Path

import pytest

from pyc_hermes_agent.asset_manager import AssetManager, calculate_asset_checksum
from pyc_hermes_agent.contracts import ModelAssetManifest


def test_asset_manager_installs_bytes_under_model_id_and_version_layout(tmp_path) -> None:
    manager = AssetManager(root=tmp_path)
    payload = b"demo-model-weights"
    manifest = ModelAssetManifest(
        asset_id="demo/embed-small",
        version="2026.05.15",
        checksum=calculate_asset_checksum(payload),
        size_bytes=len(payload),
    )

    installed = manager.install_bytes(manifest, payload, filename="weights.bin")

    assert installed.asset_dir == manager.models_dir / "demo" / "embed-small" / "2026.05.15"
    assert installed.manifest_path.exists()
    assert installed.primary_path == installed.asset_dir / "weights.bin"
    assert installed.primary_path is not None
    assert installed.primary_path.read_bytes() == payload
    assert installed.checksum == manifest.checksum


def test_asset_manager_reuses_existing_verified_install(tmp_path) -> None:
    manager = AssetManager(root=tmp_path)
    payload = b"demo-model-weights"
    manifest = ModelAssetManifest(
        asset_id="demo/embed-small",
        version="revision-1",
        checksum=calculate_asset_checksum(payload),
        size_bytes=len(payload),
    )

    first = manager.install_bytes(manifest, payload, filename="weights.bin")
    second = manager.install_bytes(manifest, payload, filename="weights.bin")

    assert second.asset_dir == first.asset_dir
    assert second.checksum == first.checksum


def test_asset_manager_validates_checksum_before_promotion(tmp_path) -> None:
    manager = AssetManager(root=tmp_path)
    manifest = ModelAssetManifest(
        asset_id="demo/embed-small",
        version="revision-1",
        checksum="sha256:" + "0" * 64,
        size_bytes=4,
    )

    with pytest.raises(ValueError, match="checksum"):
        manager.install_bytes(manifest, b"real", filename="weights.bin")

    assert manager.get_installed_asset("demo/embed-small", "revision-1") is None


def test_asset_manager_rejects_invalid_asset_path_segments(tmp_path) -> None:
    manager = AssetManager(root=tmp_path)
    payload = b"demo"
    manifest = ModelAssetManifest(
        asset_id="../escape",
        version="revision-1",
        checksum=calculate_asset_checksum(payload),
        size_bytes=len(payload),
    )

    with pytest.raises(ValueError, match="asset id"):
        manager.install_bytes(manifest, payload)


def test_asset_manager_installs_directory_payloads_atomically(tmp_path) -> None:
    source_dir = tmp_path / "source-model"
    source_dir.mkdir()
    (source_dir / "config.json").write_text('{"dim": 384}', encoding="utf-8")
    (source_dir / "weights.bin").write_bytes(b"abcd")

    manager = AssetManager(root=tmp_path)
    manifest = ModelAssetManifest(
        asset_id="demo/multi-file-model",
        version="revision-2",
        checksum=calculate_asset_checksum(source_dir),
        size_bytes=sum(path.stat().st_size for path in source_dir.iterdir()),
    )

    installed = manager.install_path(manifest, source_dir)

    assert {path.name for path in installed.files} == {"config.json", "weights.bin"}
    assert (installed.asset_dir / "config.json").read_text(encoding="utf-8") == '{"dim": 384}'
    assert installed.asset_dir.parent == manager.models_dir / "demo" / "multi-file-model"
    assert not any(path.name.startswith("stage-") for path in manager.downloads_dir.rglob("*"))


def test_asset_manager_rejects_single_file_source_with_reserved_manifest_name_before_promotion(tmp_path) -> None:
    source = tmp_path / "pyc_asset_manifest.json"
    source.write_bytes(b"model-bytes")
    manager = AssetManager(root=tmp_path)
    manifest = ModelAssetManifest(
        asset_id="demo/reserved-name-model",
        version="revision-1",
        checksum=calculate_asset_checksum(source),
        size_bytes=source.stat().st_size,
    )
    target_dir = manager.get_asset_directory(manifest.asset_id, manifest.version)

    with pytest.raises(ValueError) as excinfo:
        manager.install_path(manifest, source)

    assert not target_dir.exists()
    assert "reserved metadata file" in str(excinfo.value)
