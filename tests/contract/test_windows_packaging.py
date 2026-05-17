"""Install-directory immutability and packaging preview contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.packaging.policy import validate_runtime_paths_outside_install
from pyc_hermes_agent.packaging.probe import main as packaging_probe_main


def test_packaging_enforced_keeps_writables_off_install_dir(monkeypatch, tmp_path: Path) -> None:
    install = tmp_path / "Program Files" / "PycHermesAgent"
    install.mkdir(parents=True)
    roaming = tmp_path / "Roaming"
    local = tmp_path / "Local"
    monkeypatch.setenv("PYC_HERMES_ENFORCE_PACKAGING_RULES", "1")
    monkeypatch.setenv("PYC_HERMES_INSTALL_DIR", str(install))
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    paths = resolve_runtime_paths(install)

    assert paths.config_dir.is_relative_to(roaming.resolve())
    assert paths.models_dir.is_relative_to(local.resolve())
    assert install.resolve() not in paths.mrag_dir.resolve().parents
    assert paths.mrag_dir.resolve() != install.resolve()


def test_validate_runtime_paths_rejects_nesting_under_install(tmp_path: Path) -> None:
    install = tmp_path / "install"
    install.mkdir()
    bad_config = install / "bad" / "config"
    bad_config.mkdir(parents=True)
    paths = ensure_runtime_directories(
        resolve_runtime_paths(
            tmp_path / "workspace",
        )
    )
    # Build invalid layout by forging a path object (validation reads attributes)
    from pyc_hermes_agent.common.runtime_paths import RuntimePaths

    invalid = RuntimePaths(
        config_dir=bad_config,
        local_data_dir=paths.local_data_dir,
        logs_dir=paths.logs_dir,
        cache_dir=paths.cache_dir,
        downloads_dir=paths.downloads_dir,
        indexes_dir=paths.indexes_dir,
        models_dir=paths.models_dir,
        artifacts_dir=paths.artifacts_dir,
        mrag_dir=paths.mrag_dir,
    )
    with pytest.raises(RuntimeError) as exc:
        validate_runtime_paths_outside_install(invalid, install)
    assert "config_dir" in str(exc.value)


@pytest.mark.skipif(sys.platform == "win32", reason="Uses POSIX XDG layout for default paths.")
def test_runtime_paths_default_on_posix_uses_xdg_when_no_workspace(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    paths = resolve_runtime_paths(None)

    assert paths.config_dir == tmp_path / ".config" / "PycHermesAgent"
    assert paths.local_data_dir == tmp_path / ".local" / "share" / "PycHermesAgent"


def test_packaging_probe_reports_ok_when_install_dir_is_safe(monkeypatch, tmp_path: Path, capsys) -> None:
    install = tmp_path / "install"
    install.mkdir()
    roaming = tmp_path / "Roaming"
    local = tmp_path / "Local"
    monkeypatch.setenv("PYC_HERMES_ENFORCE_PACKAGING_RULES", "1")
    monkeypatch.setenv("PYC_HERMES_INSTALL_DIR", str(install))
    monkeypatch.setenv("APPDATA", str(roaming))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    assert packaging_probe_main(["--workspace-root", str(install)]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["install_immutability"] == "ok"
    assert Path(data["paths"]["mrag_dir"]).is_relative_to(local)
