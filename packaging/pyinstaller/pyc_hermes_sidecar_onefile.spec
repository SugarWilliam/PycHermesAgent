# -*- mode: python ; coding: utf-8 -*-
"""One-file sidecar console binary (Windows/Linux/macOS build host).

From repo root::

    uv sync --extra ga
    uv run pyinstaller --noconfirm packaging/pyinstaller/pyc_hermes_sidecar_onefile.spec

CI attaches ``dist/pyc-hermes-sidecar.exe`` on Windows runners.

``Analysis`` / ``PYZ`` / ``EXE`` are injected by PyInstaller when loading this spec.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

def _repo_root() -> Path:
    here = Path(SPECPATH).resolve().parent  # packaging/pyinstaller/
    for path in (here, *here.parents):
        if (path / "pyproject.toml").is_file() and (path / "src" / "pyc_hermes_agent").is_dir():
            return path
    raise RuntimeError("PyInstaller spec: cannot locate repository root (pyproject.toml + src/pyc_hermes_agent).")


ROOT = _repo_root()
SRC = ROOT / "src"

block_cipher = None
hiddenimports = collect_submodules("pyc_hermes_agent")

a = Analysis(
    [str(SRC / "pyc_hermes_agent" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pyc-hermes-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
