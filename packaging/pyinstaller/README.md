# PyInstaller — sidecar onefile

Spec: **`pyc_hermes_sidecar_onefile.spec`**

- Entry: **`src/pyc_hermes_agent/__main__.py`** (`python -m pyc_hermes_agent`).
- Requires **`uv sync --extra ga`** (PyInstaller 在 optional `ga` 组).

Windows 本地构建脚本：`../../scripts/build_sidecar_windows.ps1`  
CI：见仓库根目录 **`.github/workflows/release.yml`**（推送 `v*` tag 时构建 `pyc-hermes-sidecar.exe`）。
